from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db, socketio
from ..models import Alert, Device
from ..services.bandwidth import get_bandwidth
from ..services.dashboard import dashboard_payload
from ..services.network import known_subnets_payload, scan_and_persist, scan_subnet_and_persist
from ..services.pi import pi_info
from ..services.router import get_router_config, router_status
from ..services.serializers import alert_to_dict, device_to_dict
from ..services.settings import get_settings_payload, update_settings
from ..services.tools import tool_status
from ..services.updater import run_update, update_status
from ..services.wifi import connect_wifi, scan_wifi_networks, wifi_info

api_bp = Blueprint("api", __name__)


@api_bp.get("/dashboard")
@login_required
def dashboard():
    return jsonify(dashboard_payload())


@api_bp.get("/devices")
@login_required
def devices():
    rows = Device.query.order_by(Device.is_online.desc(), Device.last_seen.desc()).all()
    return jsonify([device_to_dict(device) for device in rows])


@api_bp.patch("/devices/<int:device_id>")
@login_required
def update_device(device_id: int):
    device = db.session.get(Device, device_id)
    if device is None:
        return jsonify({"error": "Không tìm thấy thiết bị"}), 404

    payload = request.get_json(silent=True) or {}
    if "custom_name" in payload:
        device.custom_name = str(payload["custom_name"])[:255]
    if "notes" in payload:
        device.notes = str(payload["notes"])
    if "is_known" in payload:
        device.is_known = bool(payload["is_known"])
    db.session.commit()
    return jsonify(device_to_dict(device))


@api_bp.post("/scan")
@login_required
def scan():
    payload = scan_and_persist()
    socketio.emit("devices:update", payload["devices"])
    for alert in payload["alerts"]:
        socketio.emit("alerts:new", alert)
    socketio.emit("dashboard:update", dashboard_payload())
    return jsonify(payload)


@api_bp.get("/subnets")
@login_required
def subnets():
    return jsonify(known_subnets_payload())


@api_bp.post("/scan/subnet")
@login_required
def scan_subnet():
    payload = request.get_json(silent=True) or {}
    try:
        result = scan_subnet_and_persist(str(payload.get("subnet", "")))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    socketio.emit("devices:update", result["devices"])
    for alert in result["alerts"]:
        socketio.emit("alerts:new", alert)
    socketio.emit("dashboard:update", dashboard_payload())
    return jsonify(result)


@api_bp.get("/wifi")
@login_required
def wifi():
    return jsonify(wifi_info())


@api_bp.get("/wifi/scan")
@login_required
def wifi_scan():
    return jsonify(scan_wifi_networks())


@api_bp.post("/wifi/connect")
@login_required
def wifi_connect():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(connect_wifi(str(payload.get("ssid", "")), str(payload.get("password", ""))))
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.get("/pi")
@login_required
def pi():
    return jsonify(pi_info())


@api_bp.get("/bandwidth")
@login_required
def bandwidth():
    range_name = request.args.get("range", "hour")
    payload = get_bandwidth(range_name)
    socketio.emit("bandwidth:update", payload)
    return jsonify(payload)


@api_bp.get("/router/status")
@login_required
def router():
    return jsonify(router_status())


@api_bp.post("/router/settings")
@login_required
def router_settings():
    router = get_router_config()
    payload = request.get_json(silent=True) or {}
    router.base_url = payload.get("base_url", router.base_url).strip() or "http://192.168.1.1"
    router.username = payload.get("username", router.username or "")
    if "password" in payload:
        router.password = payload.get("password") or ""
    db.session.commit()
    return jsonify({"router": {"base_url": router.base_url, "username": router.username, "password": bool(router.password)}})


@api_bp.get("/alerts")
@login_required
def alerts():
    rows = Alert.query.order_by(Alert.created_at.desc()).all()
    return jsonify([alert_to_dict(alert) for alert in rows])


@api_bp.post("/alerts/<int:alert_id>/ack")
@login_required
def acknowledge_alert(alert_id: int):
    alert = db.session.get(Alert, alert_id)
    if alert is None:
        return jsonify({"error": "Không tìm thấy cảnh báo"}), 404
    alert.acknowledged = True
    db.session.commit()
    return jsonify(alert_to_dict(alert))


@api_bp.get("/settings/tools")
@login_required
def tools():
    return jsonify(tool_status())


@api_bp.get("/update/status")
@login_required
def update_info():
    return jsonify(update_status())


@api_bp.post("/update")
@login_required
def update_app():
    return jsonify(run_update())


@api_bp.get("/settings")
@login_required
def settings():
    return jsonify(get_settings_payload())


@api_bp.post("/settings")
@login_required
def save_settings():
    payload = request.get_json(silent=True) or {}
    return jsonify(update_settings(payload))


@socketio.on("scan:request")
def socket_scan_request():
    if not current_user.is_authenticated:
        socketio.emit("error", {"message": "authentication_required"})
        return
    payload = scan_and_persist()
    socketio.emit("devices:update", payload["devices"])
    for alert in payload["alerts"]:
        socketio.emit("alerts:new", alert)
    socketio.emit("dashboard:update", dashboard_payload())
