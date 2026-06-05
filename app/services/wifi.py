from __future__ import annotations

import re
import shutil
import subprocess

from .network import detect_default_interface


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
