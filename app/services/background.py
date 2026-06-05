from __future__ import annotations

from flask import Flask

from ..extensions import socketio
from .bandwidth import get_bandwidth
from .dashboard import dashboard_payload
from .network import scan_and_persist
from .settings import get_setting


def start_background_tasks(app: Flask) -> None:
    if app.config.get("TESTING") or app.config.get("BACKGROUND_TASKS_STARTED"):
        return
    app.config["BACKGROUND_TASKS_STARTED"] = True
    socketio.start_background_task(_poll_loop, app)


def _poll_loop(app: Flask) -> None:
    with app.app_context():
        while True:
            interval = _scan_interval()
            try:
                scan_payload = scan_and_persist()
                bandwidth_payload = get_bandwidth("hour")
                socketio.emit("devices:update", scan_payload["devices"])
                for alert in scan_payload["alerts"]:
                    socketio.emit("alerts:new", alert)
                socketio.emit("dashboard:update", dashboard_payload())
                socketio.emit("bandwidth:update", bandwidth_payload)
            except Exception as exc:
                app.logger.exception("Background network poll failed: %s", exc)
            socketio.sleep(interval)


def _scan_interval() -> int:
    try:
        return max(15, int(get_setting("scan_interval_seconds", "60") or "60"))
    except ValueError:
        return 60
