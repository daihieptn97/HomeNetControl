from __future__ import annotations

from datetime import timedelta

import psutil
from flask import current_app

from ..extensions import db
from ..models import BandwidthSample, utcnow
from .network import detect_default_interface
from .serializers import bandwidth_sample_to_dict


RANGES = {
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(days=7),
}


def read_network_counters(interface: str | None = None) -> dict:
    interface = interface or detect_default_interface()
    counters_by_interface = psutil.net_io_counters(pernic=True)
    counters = counters_by_interface.get(interface)
    if counters is None:
        counters = psutil.net_io_counters()
    return {
        "interface": interface,
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
    }


def collect_bandwidth_sample(interface: str | None = None) -> BandwidthSample:
    interface = interface or detect_default_interface()
    counters_payload = read_network_counters(interface)

    previous = (
        BandwidthSample.query.filter_by(interface=interface)
        .order_by(BandwidthSample.sampled_at.desc())
        .first()
    )
    upload_delta = 0
    download_delta = 0
    if previous:
        upload_delta = max(0, counters_payload["bytes_sent"] - previous.bytes_sent)
        download_delta = max(0, counters_payload["bytes_recv"] - previous.bytes_recv)

    sample = BandwidthSample(
        interface=interface,
        bytes_sent=counters_payload["bytes_sent"],
        bytes_recv=counters_payload["bytes_recv"],
        upload_delta=upload_delta,
        download_delta=download_delta,
    )
    db.session.add(sample)
    db.session.commit()
    return sample


def get_bandwidth(range_name: str = "hour") -> dict:
    if range_name not in RANGES:
        range_name = "hour"
    if BandwidthSample.query.count() == 0:
        collect_bandwidth_sample()
    since = utcnow() - RANGES[range_name]
    samples = (
        BandwidthSample.query.filter(BandwidthSample.sampled_at >= since)
        .order_by(BandwidthSample.sampled_at.asc())
        .all()
    )
    if not samples and current_app.config.get("MOCK_DATA"):
        samples = [collect_bandwidth_sample()]
    return {
        "range": range_name,
        "samples": [bandwidth_sample_to_dict(sample) for sample in samples],
        "per_device_available": False,
        "per_device": [],
    }
