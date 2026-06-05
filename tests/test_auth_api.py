from app.models import User


def test_default_admin_created_with_hashed_password(app):
    with app.app_context():
        user = User.query.filter_by(username="admin").one()
        assert user.password_hash != "admin"
        assert user.check_password("admin")


def test_login_and_api_protection(client):
    protected = client.get("/api/dashboard")
    assert protected.status_code in {302, 401}

    response = client.post("/login", data={"username": "admin", "password": "admin"}, follow_redirects=False)
    assert response.status_code == 302

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert "devices" in dashboard.get_json()


def test_scan_devices_and_update(logged_in):
    scan = logged_in.post("/api/scan")
    assert scan.status_code == 200
    devices = logged_in.get("/api/devices").get_json()
    assert len(devices) >= 1

    first = devices[0]
    update = logged_in.patch(
        f"/api/devices/{first['id']}",
        json={"custom_name": "Router chính", "notes": "Ghi chú", "is_known": True},
    )
    assert update.status_code == 200
    payload = update.get_json()
    assert payload["custom_name"] == "Router chính"
    assert payload["is_known"] is True


def test_settings_and_router_endpoints(logged_in):
    settings = logged_in.post(
        "/api/settings",
        json={"network_interface": "wlan0", "network_subnet": "192.168.1.0/24", "scan_interval_seconds": 90},
    )
    assert settings.status_code == 200
    assert settings.get_json()["network_interface"] == "wlan0"

    router = logged_in.post("/api/router/settings", json={"base_url": "http://192.168.1.1", "username": "admin"})
    assert router.status_code == 200
    assert router.get_json()["router"]["base_url"] == "http://192.168.1.1"


def test_alert_ack(logged_in):
    logged_in.post("/api/scan")
    alerts = logged_in.get("/api/alerts").get_json()
    assert alerts
    ack = logged_in.post(f"/api/alerts/{alerts[0]['id']}/ack")
    assert ack.status_code == 200
    assert ack.get_json()["acknowledged"] is True
