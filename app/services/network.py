from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from itertools import islice

import psutil
from flask import current_app

from ..extensions import db
from ..models import Alert, Device, DeviceObservation, KnownSubnet, utcnow
from .serializers import device_to_dict, known_subnet_to_dict
from .settings import get_setting


@dataclass
class ScanDevice:
    ip: str
    mac: str
    hostname: str = ""
    vendor: str = ""


ARP_SCAN_RE = re.compile(
    r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+(?P<mac>[0-9a-fA-F:]{17})\s*(?P<vendor>.*)$"
)
NMAP_HOST_RE = re.compile(r"Nmap scan report for (?:(?P<host>.+?) \()?((?P<ip>\d+\.\d+\.\d+\.\d+))\)?")
NMAP_MAC_RE = re.compile(r"MAC Address:\s+(?P<mac>[0-9A-Fa-f:]{17})(?:\s+\((?P<vendor>.+)\))?")


def normalize_mac(mac: str) -> str:
    return mac.strip().lower()


def detect_default_interface() -> str:
    configured = get_setting("network_interface")
    if configured:
        return configured
    stats = psutil.net_if_stats()
    for name, stat in stats.items():
        if stat.isup and not name.startswith(("lo", "utun", "awdl", "llw")):
            return name
    return next(iter(stats), "eth0")


def detect_subnet(interface: str | None = None) -> str:
    configured = get_setting("network_subnet")
    if configured:
        return configured
    interface = interface or detect_default_interface()
    addresses = psutil.net_if_addrs().get(interface, [])
    for addr in addresses:
        if addr.family == socket.AF_INET and addr.netmask:
            network = ipaddress.IPv4Network(f"{addr.address}/{addr.netmask}", strict=False)
            return str(network)
    return "192.168.1.0/24"


def parse_arp_scan(output: str) -> list[ScanDevice]:
    devices = []
    for line in output.splitlines():
        match = ARP_SCAN_RE.match(line.strip())
        if match:
            devices.append(
                ScanDevice(
                    ip=match.group("ip"),
                    mac=normalize_mac(match.group("mac")),
                    vendor=(match.group("vendor") or "").strip(),
                )
            )
    return devices


def parse_nmap(output: str) -> list[ScanDevice]:
    devices: list[ScanDevice] = []
    current_ip = ""
    current_host = ""
    for line in output.splitlines():
        host_match = NMAP_HOST_RE.search(line)
        if host_match:
            current_ip = host_match.group("ip")
            current_host = (host_match.group("host") or "").strip()
            continue
        mac_match = NMAP_MAC_RE.search(line)
        if mac_match and current_ip:
            devices.append(
                ScanDevice(
                    ip=current_ip,
                    mac=normalize_mac(mac_match.group("mac")),
                    hostname=current_host if current_host != current_ip else "",
                    vendor=(mac_match.group("vendor") or "").strip(),
                )
            )
            current_ip = ""
            current_host = ""
    return devices


def validate_subnet(subnet: str) -> str:
    try:
        network = ipaddress.IPv4Network(subnet, strict=False)
    except ValueError as exc:
        raise ValueError("Subnet không hợp lệ") from exc
    return str(network)


def remember_subnet(subnet: str, interface: str = "", ssid: str = "", scanned: bool = False) -> KnownSubnet:
    normalized = validate_subnet(subnet)
    now = utcnow()
    row = KnownSubnet.query.filter_by(subnet=normalized).first()
    if row is None:
        row = KnownSubnet(subnet=normalized, first_seen=now)
        db.session.add(row)
    row.interface = interface or row.interface
    row.ssid = ssid or row.ssid
    row.last_seen = now
    if scanned:
        row.last_scanned_at = now
    return row


def known_subnets_payload() -> list[dict]:
    rows = KnownSubnet.query.order_by(KnownSubnet.last_seen.desc()).all()
    return [known_subnet_to_dict(row) for row in rows]


def scan_network(subnet: str | None = None, interface: str | None = None) -> list[ScanDevice]:
    mock_enabled = get_setting("mock_data", "true" if current_app.config.get("MOCK_DATA") else "false") == "true"
    interface = interface or detect_default_interface()
    current_subnet = detect_subnet(interface)
    target_subnet = validate_subnet(subnet or current_subnet)
    if mock_enabled and not (shutil.which("arp-scan") or shutil.which("nmap")):
        return mock_devices(target_subnet)

    if target_subnet == current_subnet and shutil.which("arp-scan"):
        completed = subprocess.run(
            ["arp-scan", "--localnet", "--interface", interface],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        devices = parse_arp_scan(completed.stdout)
        if devices:
            return devices

    if shutil.which("nmap"):
        completed = subprocess.run(
            ["nmap", "-sn", target_subnet],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        devices = parse_nmap(completed.stdout)
        if devices:
            return devices

    return mock_devices(target_subnet) if mock_enabled else []


def mock_devices(subnet: str = "192.168.1.0/24") -> list[ScanDevice]:
    network = ipaddress.IPv4Network(validate_subnet(subnet), strict=False)
    hosts = list(islice(network.hosts(), 44))
    gateway = str(hosts[0]) if hosts else "192.168.1.1"
    pi = str(hosts[11]) if len(hosts) > 11 else gateway
    phone = str(hosts[43]) if len(hosts) > 43 else gateway
    return [
        ScanDevice(gateway, "aa:bb:cc:00:00:01", "router.local", "Generic Router"),
        ScanDevice(pi, "aa:bb:cc:00:00:12", "raspberrypi", "Raspberry Pi"),
        ScanDevice(phone, "aa:bb:cc:00:00:44", "phone", "Unknown Vendor"),
    ]


def persist_scan(devices: list[ScanDevice], mark_missing_offline: bool = True) -> tuple[list[Device], list[Alert]]:
    now = utcnow()
    seen_macs = {normalize_mac(item.mac) for item in devices if item.mac}
    if mark_missing_offline:
        Device.query.update({Device.is_online: False})

    persisted: list[Device] = []
    alerts: list[Alert] = []
    for item in devices:
        mac = normalize_mac(item.mac)
        if not mac:
            continue
        device = Device.query.filter_by(mac=mac).first()
        is_new = device is None
        if is_new:
            device = Device(mac=mac, first_seen=now, is_known=False)
            db.session.add(device)
        device.ip = item.ip
        device.hostname = item.hostname
        device.vendor = item.vendor
        device.last_seen = now
        device.is_online = True
        db.session.flush()
        db.session.add(
            DeviceObservation(
                device_id=device.id,
                ip=item.ip,
                hostname=item.hostname,
                vendor=item.vendor,
                observed_at=now,
            )
        )
        if is_new:
            alert = Alert(
                type="unknown_device",
                severity="warning",
                message=f"Phát hiện thiết bị mới: {item.ip} ({mac})",
                device_id=device.id,
            )
            db.session.add(alert)
            alerts.append(alert)
        persisted.append(device)

    if mark_missing_offline and not seen_macs:
        Device.query.update({Device.is_online: False})
    db.session.commit()
    return persisted, alerts


def scan_and_persist() -> dict:
    interface = detect_default_interface()
    subnet = detect_subnet(interface)
    remember_subnet(subnet, interface=interface, scanned=True)
    devices, alerts = persist_scan(scan_network(subnet=subnet, interface=interface))
    return {
        "devices": [device_to_dict(device) for device in devices],
        "alerts": [{"id": alert.id, "message": alert.message} for alert in alerts],
        "scanned_at": utcnow().isoformat(),
        "subnet": subnet,
    }


def scan_subnet_and_persist(subnet: str) -> dict:
    normalized = validate_subnet(subnet)
    interface = detect_default_interface()
    known = remember_subnet(normalized, interface=interface, scanned=True)
    devices, alerts = persist_scan(scan_network(subnet=normalized, interface=interface), mark_missing_offline=False)
    db.session.commit()
    return {
        "subnet": known_subnet_to_dict(known),
        "devices": [device_to_dict(device) for device in devices],
        "alerts": [{"id": alert.id, "message": alert.message} for alert in alerts],
        "scanned_at": utcnow().isoformat(),
    }
