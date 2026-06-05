from __future__ import annotations

from flask import Blueprint, redirect, render_template, url_for
from flask_login import login_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return redirect(url_for("pages.dashboard"))


@pages_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active="dashboard", title="Dashboard")


@pages_bp.route("/devices")
@login_required
def devices():
    return render_template("devices.html", active="devices", title="Thiết bị mạng")


@pages_bp.route("/wifi")
@login_required
def wifi():
    return render_template("wifi.html", active="wifi", title="Thông tin WiFi")


@pages_bp.route("/bandwidth")
@login_required
def bandwidth():
    return render_template("bandwidth.html", active="bandwidth", title="Băng thông")


@pages_bp.route("/router")
@login_required
def router():
    return render_template("router.html", active="router", title="Router")


@pages_bp.route("/alerts")
@login_required
def alerts():
    return render_template("alerts.html", active="alerts", title="Cảnh báo")


@pages_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active="settings", title="Cài đặt")
