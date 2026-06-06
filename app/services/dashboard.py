from __future__ import annotations

import platform

import psutil

from ..models import Alert, Device
from .bandwidth import read_network_counters
from .network import detect_default_interface, detect_subnet
from .serializers import alert_to_dict


def dashboard_payload() -> dict:
    interface = detect_default_interface()
    counters = read_network_counters(interface)
    return {
        "devices": {
            "online": Device.query.filter_by(is_online=True).count(),
            "known": Device.query.filter_by(is_known=True).count(),
            "unknown": Device.query.filter_by(is_known=False).count(),
            "total": Device.query.count(),
        },
        "network": {
            "interface": interface,
            "subnet": detect_subnet(interface),
            "bytes_sent": counters["bytes_sent"],
            "bytes_recv": counters["bytes_recv"],
        },
        "system": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "boot_time": psutil.boot_time(),
        },
        "latest_alerts": [
            alert_to_dict(alert)
            for alert in Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
        ],
    }
