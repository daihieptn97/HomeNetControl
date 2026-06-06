from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    load_dotenv(BASE_DIR / ".env")

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-only-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'homenetcontrol.sqlite3'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    NETWORK_INTERFACE = os.getenv("NETWORK_INTERFACE", "")
    NETWORK_SUBNET = os.getenv("NETWORK_SUBNET", "")
    SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "60"))
    ROUTER_URL = os.getenv("ROUTER_URL", "http://192.168.1.1")
    ROUTER_USERNAME = os.getenv("ROUTER_USERNAME", "")
    ROUTER_PASSWORD = os.getenv("ROUTER_PASSWORD", "")
    MOCK_DATA = _bool_env("MOCK_DATA", True)
    DEBUG = _bool_env("FLASK_DEBUG", False)


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin"
    MOCK_DATA = True
