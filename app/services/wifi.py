from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from ..extensions import db
from .network import detect_default_interface, detect_subnet, remember_subnet


@dataclass
class WifiNetwork:
    ssid: str
    signal_dbm: int | None = None
    signal_percent: int | None = None
    frequency_mhz: int | None = None
    band: str = ""
    channel: str = ""
    security: str = ""
    bssid: str = ""
    source: str = ""


def parse_iw_link(output: str) -> dict:
    data = {
        "ssid": "",
        "signal_dbm": None,
        "channel": "",
        "band": "",
        "frequency_mhz": None,
        "tx_bitrate": "",
    }
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            data["ssid"] = line.split(":", 1)[1].strip()
        elif line.startswith("signal:"):
            match = re.search(r"(-?\d+)", line)
            data["signal_dbm"] = int(match.group(1)) if match else None
        elif line.startswith("freq:"):
            match = re.search(r"(\d+)", line)
            if match:
                freq = int(match.group(1))
                data["frequency_mhz"] = freq
                data["band"] = "5 GHz" if freq >= 5000 else "2.4 GHz"
        elif line.startswith("tx bitrate:"):
            data["tx_bitrate"] = line.split(":", 1)[1].strip()
    return data


def parse_iw_dev(output: str) -> dict:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("channel "):
            parts = line.split()
            return {"channel": parts[1] if len(parts) > 1 else ""}
    return {"channel": ""}


def parse_iw_scan(output: str) -> list[dict]:
    networks: list[WifiNetwork] = []
    current: WifiNetwork | None = None
    security: set[str] = set()

    def finish() -> None:
        nonlocal current, security
        if current is None:
            return
        if not current.ssid:
            current.ssid = "(ẩn)"
        current.security = ", ".join(sorted(security)) if security else ("WEP/Protected" if current.security else "Open")
        current.source = "iw"
        networks.append(current)
        current = None
        security = set()

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line.startswith("BSS "):
            finish()
            bssid = line.split()[1].split("(", 1)[0]
            current = WifiNetwork(ssid="", bssid=bssid)
        elif current and line.startswith("SSID:"):
            current.ssid = line.split(":", 1)[1].strip()
        elif current and line.startswith("signal:"):
            match = re.search(r"(-?\d+(?:\.\d+)?)", line)
            current.signal_dbm = round(float(match.group(1))) if match else None
        elif current and line.startswith("freq:"):
            match = re.search(r"(\d+)", line)
            if match:
                current.frequency_mhz = int(match.group(1))
                current.band = "5 GHz" if current.frequency_mhz >= 5000 else "2.4 GHz"
                current.channel = channel_from_frequency(current.frequency_mhz)
        elif current and line.startswith("capability:") and "Privacy" in line:
            current.security = "protected"
        elif current and line.startswith("RSN:"):
            security.add("WPA2/RSN")
        elif current and line.startswith("WPA:"):
            security.add("WPA")

    finish()
    return [wifi_network_to_dict(network) for network in _dedupe_networks(networks)]


def parse_nmcli_wifi(output: str) -> list[dict]:
    networks: list[WifiNetwork] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = split_nmcli_line(line)
        if len(parts) < 4:
            continue
        ssid, signal, frequency, security = parts[:4]
        if not ssid:
            ssid = "(ẩn)"
        frequency_mhz = int(frequency) if frequency.isdigit() else None
        networks.append(
            WifiNetwork(
                ssid=ssid,
                signal_percent=int(signal) if signal.isdigit() else None,
                frequency_mhz=frequency_mhz,
                band=("5 GHz" if frequency_mhz and frequency_mhz >= 5000 else "2.4 GHz" if frequency_mhz else ""),
                channel=channel_from_frequency(frequency_mhz) if frequency_mhz else "",
                security=security or "Open",
                source="nmcli",
            )
        )
    return [wifi_network_to_dict(network) for network in _dedupe_networks(networks)]


def split_nmcli_line(line: str) -> list[str]:
    parts: list[str] = []
    current = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def channel_from_frequency(frequency_mhz: int) -> str:
    if 2412 <= frequency_mhz <= 2472:
        return str((frequency_mhz - 2407) // 5)
    if frequency_mhz == 2484:
        return "14"
    if 5000 <= frequency_mhz <= 5900:
        return str((frequency_mhz - 5000) // 5)
    return ""


def wifi_network_to_dict(network: WifiNetwork) -> dict:
    return {
        "ssid": network.ssid,
        "signal_dbm": network.signal_dbm,
        "signal_percent": network.signal_percent,
        "frequency_mhz": network.frequency_mhz,
        "band": network.band,
        "channel": network.channel,
        "security": network.security,
        "bssid": network.bssid,
        "source": network.source,
    }


def _dedupe_networks(networks: list[WifiNetwork]) -> list[WifiNetwork]:
    best: dict[str, WifiNetwork] = {}
    for network in networks:
        score = network.signal_percent if network.signal_percent is not None else network.signal_dbm or -999
        previous = best.get(network.ssid)
        previous_score = (
            previous.signal_percent if previous and previous.signal_percent is not None else previous.signal_dbm if previous else -999
        )
        if previous is None or score > previous_score:
            best[network.ssid] = network
    return sorted(best.values(), key=lambda item: item.signal_percent if item.signal_percent is not None else item.signal_dbm or -999, reverse=True)


def scan_wifi_networks() -> dict:
    interface = detect_default_interface()
    if shutil.which("nmcli"):
        completed = subprocess.run(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,FREQ,SECURITY", "dev", "wifi", "list", "ifname", interface, "--rescan", "yes"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        networks = parse_nmcli_wifi(completed.stdout)
        if networks:
            return {"interface": interface, "source": "nmcli", "networks": networks}

    if shutil.which("iw"):
        completed = subprocess.run(
            ["iw", "dev", interface, "scan"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        networks = parse_iw_scan(completed.stdout)
        if networks:
            return {"interface": interface, "source": "iw", "networks": networks}

    return {
        "interface": interface,
        "source": "mock",
        "networks": [
            wifi_network_to_dict(WifiNetwork("HomeNet", signal_dbm=-48, signal_percent=88, frequency_mhz=2437, band="2.4 GHz", channel="6", security="WPA2", source="mock")),
            wifi_network_to_dict(WifiNetwork("HomeNet-5G", signal_dbm=-57, signal_percent=74, frequency_mhz=5180, band="5 GHz", channel="36", security="WPA2", source="mock")),
            wifi_network_to_dict(WifiNetwork("Guest", signal_dbm=-69, signal_percent=46, frequency_mhz=2462, band="2.4 GHz", channel="11", security="WPA2", source="mock")),
        ],
    }


def connect_wifi(ssid: str, password: str = "") -> dict:
    ssid = (ssid or "").strip()
    if not ssid or ssid == "(ẩn)":
        raise ValueError("SSID không hợp lệ")
    interface = detect_default_interface()
    if not shutil.which("nmcli"):
        raise RuntimeError("Thiếu nmcli nên chưa thể kết nối WiFi từ web. Cài NetworkManager/nmcli trên Raspberry Pi.")

    command = ["nmcli", "dev", "wifi", "connect", ssid]
    if password:
        command.extend(["password", password])
    command.extend(["ifname", interface])
    completed = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    if completed.returncode != 0:
        message = scrub_secret((completed.stderr or completed.stdout or "Kết nối WiFi thất bại").strip(), password)
        raise RuntimeError(message)

    subnet = detect_subnet(interface)
    remember_subnet(subnet, interface=interface, ssid=ssid)
    db.session.commit()
    return {
        "connected": True,
        "interface": interface,
        "ssid": ssid,
        "subnet": subnet,
        "message": scrub_secret((completed.stdout or "Đã kết nối WiFi").strip(), password),
    }


def scrub_secret(value: str, secret: str) -> str:
    return value.replace(secret, "***") if secret else value


def wifi_info() -> dict:
    interface = detect_default_interface()
    data = {
        "interface": interface,
        "ssid": "HomeNet",
        "signal_dbm": None,
        "signal_quality": "Không rõ",
        "channel": "",
        "band": "",
        "frequency_mhz": None,
        "tx_bitrate": "",
        "connected_devices": None,
        "source": "mock",
    }
    if shutil.which("iw"):
        link = subprocess.run(["iw", "dev", interface, "link"], capture_output=True, text=True, timeout=5, check=False)
        dev = subprocess.run(["iw", "dev", interface, "info"], capture_output=True, text=True, timeout=5, check=False)
        data.update(parse_iw_link(link.stdout))
        data.update(parse_iw_dev(dev.stdout))
        data["source"] = "iw"
    elif shutil.which("iwconfig"):
        iwconfig = subprocess.run(["iwconfig", interface], capture_output=True, text=True, timeout=5, check=False)
        data.update(parse_iwconfig(iwconfig.stdout))
        data["source"] = "iwconfig"

    if data["signal_dbm"] is not None:
        data["signal_quality"] = signal_quality(data["signal_dbm"])
    subnet = detect_subnet(interface)
    data["subnet"] = subnet
    remember_subnet(subnet, interface=interface, ssid=data["ssid"])
    db.session.commit()
    return data


def parse_iwconfig(output: str) -> dict:
    data = {"ssid": "", "signal_dbm": None, "channel": "", "band": "", "frequency_mhz": None, "tx_bitrate": ""}
    ssid_match = re.search(r'ESSID:"([^"]+)"', output)
    if ssid_match:
        data["ssid"] = ssid_match.group(1)
    signal_match = re.search(r"Signal level=(-?\d+)", output)
    if signal_match:
        data["signal_dbm"] = int(signal_match.group(1))
    freq_match = re.search(r"Frequency:(\d+\.\d+)", output)
    if freq_match:
        freq = float(freq_match.group(1))
        data["frequency_mhz"] = int(freq * 1000)
        data["band"] = "5 GHz" if freq >= 5 else "2.4 GHz"
    bitrate_match = re.search(r"Bit Rate=([^\s]+\s+\S+)", output)
    if bitrate_match:
        data["tx_bitrate"] = bitrate_match.group(1)
    return data


def signal_quality(dbm: int) -> str:
    if dbm >= -50:
        return "Rất tốt"
    if dbm >= -60:
        return "Tốt"
    if dbm >= -70:
        return "Trung bình"
    return "Yếu"
