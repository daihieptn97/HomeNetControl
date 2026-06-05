from __future__ import annotations

from urllib.parse import urlparse

import requests

from ..extensions import db
from ..models import RouterConfig
from .serializers import model_to_dict


def get_router_config() -> RouterConfig:
    router = RouterConfig.query.first()
    if router is None:
        router = RouterConfig()
        db.session.add(router)
        db.session.commit()
    return router


def router_status() -> dict:
    router = get_router_config()
    parsed = urlparse(router.base_url)
    status = {
        "config": model_to_dict(router),
        "reachable": False,
        "status_code": None,
        "latency_ms": None,
        "wan": {},
        "lan": {},
        "dhcp_leases": [],
        "message": "Chưa kiểm tra",
    }
    if not parsed.scheme or not parsed.netloc:
        status["message"] = "Router URL không hợp lệ"
        return status

    auth = (router.username, router.password) if router.username and router.password else None
    try:
        response = requests.get(router.base_url, auth=auth, timeout=4)
    except requests.RequestException as exc:
        status["message"] = str(exc)
        return status

    status.update(
        {
            "reachable": response.ok or response.status_code in {401, 403},
            "status_code": response.status_code,
            "latency_ms": int(response.elapsed.total_seconds() * 1000),
            "message": "Router phản hồi" if response.ok else "Router yêu cầu xác thực hoặc từ chối truy cập",
        }
    )
    status.update(parse_generic_router_response(response))
    return status


def parse_generic_router_response(response: requests.Response) -> dict:
    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return {}
    try:
        body = response.json()
    except ValueError:
        return {}
    return {
        "wan": body.get("wan", {}) if isinstance(body, dict) else {},
        "lan": body.get("lan", {}) if isinstance(body, dict) else {},
        "dhcp_leases": body.get("dhcp_leases", []) if isinstance(body, dict) else [],
    }
