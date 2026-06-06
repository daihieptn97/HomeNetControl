from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac = db.Column(db.String(32), unique=True, nullable=False, index=True)
    ip = db.Column(db.String(64), nullable=False)
    hostname = db.Column(db.String(255), default="")
    vendor = db.Column(db.String(255), default="")
    custom_name = db.Column(db.String(255), default="")
    notes = db.Column(db.Text, default="")
    is_known = db.Column(db.Boolean, default=False, nullable=False)
    is_online = db.Column(db.Boolean, default=True, nullable=False)
    first_seen = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class DeviceObservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=False, index=True)
    ip = db.Column(db.String(64), nullable=False)
    hostname = db.Column(db.String(255), default="")
    vendor = db.Column(db.String(255), default="")
    observed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    device = db.relationship("Device", backref="observations")


class KnownSubnet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subnet = db.Column(db.String(64), unique=True, nullable=False, index=True)
    interface = db.Column(db.String(64), default="")
    ssid = db.Column(db.String(255), default="")
    first_seen = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_scanned_at = db.Column(db.DateTime(timezone=True), nullable=True)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(32), default="info", nullable=False)
    message = db.Column(db.String(500), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey("device.id"), nullable=True, index=True)
    acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    device = db.relationship("Device")


class Setting(db.Model):
    key = db.Column(db.String(120), primary_key=True)
    value = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class BandwidthSample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interface = db.Column(db.String(64), nullable=False, index=True)
    bytes_sent = db.Column(db.BigInteger, nullable=False)
    bytes_recv = db.Column(db.BigInteger, nullable=False)
    upload_delta = db.Column(db.BigInteger, default=0, nullable=False)
    download_delta = db.Column(db.BigInteger, default=0, nullable=False)
    sampled_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class RouterConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String(255), default="http://192.168.1.1", nullable=False)
    username = db.Column(db.String(255), default="")
    password = db.Column(db.String(255), default="")
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)
