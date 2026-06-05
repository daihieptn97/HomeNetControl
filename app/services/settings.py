from __future__ import annotations

from .serializers import model_to_dict
from ..extensions import db
from ..models import RouterConfig, Setting


def get_setting(key: str, default: str = "") -> str:
    setting = db.session.get(Setting, key)
    return setting.value if setting else default


def set_setting(key: str, value: str, commit: bool = True) -> Setting:
    setting = db.session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    if commit:
        db.session.commit()
    return setting


def get_settings_payload() -> dict:
    router = RouterConfig.query.first()
    return {
        "network_interface": get_setting("network_interface"),
        "network_subnet": get_setting("network_subnet"),
        "scan_interval_seconds": int(get_setting("scan_interval_seconds", "60") or "60"),
        "mock_data": get_setting("mock_data", "true") == "true",
        "router": model_to_dict(router) if router else None,
    }


def update_settings(payload: dict) -> dict:
    allowed = {
        "network_interface",
        "network_subnet",
        "scan_interval_seconds",
        "mock_data",
    }
    for key in allowed:
        if key in payload:
            set_setting(key, str(payload[key]), commit=False)

    router_payload = payload.get("router") or {}
    if router_payload:
        router = RouterConfig.query.first() or RouterConfig()
        router.base_url = router_payload.get("base_url", router.base_url).strip() or "http://192.168.1.1"
        router.username = router_payload.get("username", router.username or "")
        if "password" in router_payload:
            router.password = router_payload.get("password") or ""
        db.session.add(router)

    db.session.commit()
    return get_settings_payload()
