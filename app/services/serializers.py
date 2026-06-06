from __future__ import annotations

from datetime import datetime


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def device_to_dict(device) -> dict:
    return {
        "id": device.id,
        "mac": device.mac,
        "ip": device.ip,
        "hostname": device.hostname,
        "vendor": device.vendor,
        "custom_name": device.custom_name,
        "notes": device.notes,
        "is_known": device.is_known,
        "is_online": device.is_online,
        "first_seen": iso(device.first_seen),
        "last_seen": iso(device.last_seen),
        "display_name": device.custom_name or device.hostname or device.ip,
    }


def alert_to_dict(alert) -> dict:
    return {
        "id": alert.id,
        "type": alert.type,
        "severity": alert.severity,
        "message": alert.message,
        "device_id": alert.device_id,
        "acknowledged": alert.acknowledged,
        "created_at": iso(alert.created_at),
    }


def known_subnet_to_dict(subnet) -> dict:
    return {
        "id": subnet.id,
        "subnet": subnet.subnet,
        "interface": subnet.interface,
        "ssid": subnet.ssid,
        "first_seen": iso(subnet.first_seen),
        "last_seen": iso(subnet.last_seen),
        "last_scanned_at": iso(subnet.last_scanned_at),
    }


def bandwidth_sample_to_dict(sample) -> dict:
    return {
        "id": sample.id,
        "interface": sample.interface,
        "bytes_sent": sample.bytes_sent,
        "bytes_recv": sample.bytes_recv,
        "upload_delta": sample.upload_delta,
        "download_delta": sample.download_delta,
        "sampled_at": iso(sample.sampled_at),
    }


def model_to_dict(model) -> dict | None:
    if model is None:
        return None
    data = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if column.name == "password":
            value = bool(value)
        elif isinstance(value, datetime):
            value = iso(value)
        data[column.name] = value
    return data
