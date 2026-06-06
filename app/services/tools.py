from __future__ import annotations

import shutil
import subprocess


TOOLS = {
    "nmap": "sudo apt install -y nmap",
    "arp-scan": "sudo apt install -y arp-scan",
    "iw": "sudo apt install -y iw",
    "iwconfig": "sudo apt install -y wireless-tools",
    "nmcli": "sudo apt install -y network-manager",
    "ifconfig": "sudo apt install -y net-tools",
    "arp": "sudo apt install -y net-tools",
    "vnstat": "sudo apt install -y vnstat",
    "curl": "sudo apt install -y curl",
    "cloudflared": "Xem trạng thái tunnel đã triển khai sẵn trên máy",
}


def tool_status() -> list[dict]:
    result = []
    for name, install_command in TOOLS.items():
        path = shutil.which(name)
        version = ""
        if path:
            version = _version(name)
        result.append(
            {
                "name": name,
                "available": bool(path),
                "path": path or "",
                "version": version,
                "install_command": install_command,
            }
        )
    return result


def _version(name: str) -> str:
    commands = {
        "nmap": [name, "--version"],
        "arp-scan": [name, "--version"],
        "iw": [name, "--version"],
        "iwconfig": [name, "--version"],
        "nmcli": [name, "--version"],
        "ifconfig": [name, "--version"],
        "arp": [name, "--version"],
        "vnstat": [name, "--version"],
        "curl": [name, "--version"],
        "cloudflared": [name, "--version"],
    }
    try:
        completed = subprocess.run(
            commands[name],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except Exception:
        return ""
    return (completed.stdout or completed.stderr).splitlines()[0][:160] if (completed.stdout or completed.stderr) else ""
