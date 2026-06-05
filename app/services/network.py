from __future__ import annotations

import ipaddress
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass

import psutil
from flask import current_app

from ..extensions import db
from ..models import Alert, Device, DeviceObservation, utcnow
from .serializers import device_to_dict
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


def scan_network() -> list[ScanDevice]:
    mock_enabled = get_setting("mock_data", "true" if current_app.config.get("MOCK_DATA") else "false") == "true"
    if mock_enabled and not (shutil.which("arp-scan") or shutil.which("nmap")):
        return mock_devices()

    interface = detect_default_interface()
    subnet = detect_subnet(interface)
    if shutil.which("arp-scan"):
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
            ["nmap", "-sn", subnet],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        devices = parse_nmap(completed.stdout)
        if devices:
            return devices

    return mock_devices() if mock_enabled else []


def mock_devices() -> list[ScanDevice]:
    return [
        ScanDevice("192.168.1.1", "aa:bb:cc:00:00:01", "router.local", "Generic Router"),
        ScanDevice("192.168.1.12", "aa:bb:cc:00:00:12", "raspberrypi", "Raspberry Pi"),
        ScanDevice("192.168.1.44", "aa:bb:cc:00:00:44", "phone", "Unknown Vendor"),
    ]


def persist_scan(devices: list[ScanDevice]) -> tuple[list[Device], list[Alert]]:
    now = utcnow()
    seen_macs = {normalize_mac(item.mac) for item in devices if item.mac}
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

    if not seen_macs:
        Device.query.update({Device.is_online: False})
    db.session.commit()
    return persisted, alerts


def scan_and_persist() -> dict:
    devices, alerts = persist_scan(scan_network())
    return {
        "devices": [device_to_dict(device) for device in devices],
        "alerts": [{"id": alert.id, "message": alert.message} for alert in alerts],
        "scanned_at": utcnow().isoformat(),
    }
