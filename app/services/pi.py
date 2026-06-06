from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

import psutil

from .network import detect_default_interface, detect_subnet


def pi_info() -> dict:
    interface = detect_default_interface()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    swap = psutil.swap_memory()
    counters = psutil.net_io_counters(pernic=True).get(interface)
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "boot_time": psutil.boot_time(),
        "uptime_seconds": int(_uptime_seconds()),
        "cpu": {
            "percent": psutil.cpu_percent(interval=None),
            "count": psutil.cpu_count(logical=True),
            "physical_count": psutil.cpu_count(logical=False),
            "frequency_mhz": _cpu_frequency(),
            "temperature_c": _cpu_temperature(),
            "throttled": _vcgencmd("get_throttled"),
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "percent": memory.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        },
        "network": {
            "interface": interface,
            "subnet": detect_subnet(interface),
            "addresses": _interface_addresses(interface),
            "bytes_sent": counters.bytes_sent if counters else None,
            "bytes_recv": counters.bytes_recv if counters else None,
        },
    }


def _uptime_seconds() -> float:
    return time.time() - psutil.boot_time()


def _cpu_frequency() -> float | None:
    frequency = psutil.cpu_freq()
    return round(frequency.current, 1) if frequency else None


def _cpu_temperature() -> float | None:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    if path.exists():
        try:
            return round(int(path.read_text(encoding="utf-8").strip()) / 1000, 1)
        except (OSError, ValueError):
            pass
    output = _vcgencmd("measure_temp")
    if not output:
        return None
    try:
        return float(output.split("=", 1)[1].split("'", 1)[0])
    except (IndexError, ValueError):
        return None


def _vcgencmd(argument: str) -> str:
    command = shutil.which("vcgencmd")
    if not command:
        return ""
    try:
        completed = subprocess.run([command, argument], capture_output=True, text=True, timeout=3, check=False)
    except Exception:
        return ""
    return (completed.stdout or completed.stderr).strip()


def _interface_addresses(interface: str) -> list[dict]:
    rows = []
    for address in psutil.net_if_addrs().get(interface, []):
        family = "IPv4" if address.family == socket.AF_INET else "IPv6" if address.family == socket.AF_INET6 else str(address.family)
        rows.append(
            {
                "family": family,
                "address": address.address,
                "netmask": address.netmask,
                "broadcast": address.broadcast,
            }
        )
    return rows
