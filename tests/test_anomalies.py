"""Tests for the rule-based anomaly detection engine.

Each test exercises one rule in isolation by injecting exactly the events or
state needed to trigger (or suppress) that rule, keeping tests deterministic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.memory import MEMORY_STORE, MemoryStore
from app.services.anomaly_service import detect_anomalies
from pipeline.layout import Layout, Zone

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc


def _ts(offset_seconds: int = 0) -> str:
    return (datetime(2026, 4, 10, 12, 0, 0, tzinfo=UTC) + timedelta(seconds=offset_seconds)).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _base_event(
    store_id: str,
    event_type: str,
    visitor_id: str,
    session_id: str,
    *,
    offset: int = 0,
    zone_id: str | None = None,
    payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ev: Dict[str, Any] = {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": event_type,
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": zone_id,
        "payload": payload or {},
        "idempotency_key": _uid(),
    }
    return ev


def _ingest(events: list) -> None:
    resp = client.post("/events/ingest", json={"events": events})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Isolated unit tests against a fresh MemoryStore (no shared state)
# ---------------------------------------------------------------------------


def _fresh_store_with_layout(store_id: str) -> MemoryStore:
    """Return a clean MemoryStore with a minimal layout registered."""
    store = MemoryStore()
    zones = [
        Zone(
            zone_id="FOH",
            label="Front Of House",
            zone_type="floor",
            polygon=[(0, 0), (500, 0), (500, 500), (0, 500)],
        ),
        Zone(
            zone_id="SKINCARE",
            label="Skincare",
            zone_type="brand",
            polygon=[(500, 0), (1000, 0), (1000, 500), (500, 500)],
        ),
    ]
    layout = Layout(
        store_id=store_id,
        image_width=1000,
        image_height=500,
        zones=zones,
        zones_by_id={z.zone_id: z for z in zones},
    )
    store.register_layout(store_id, layout)
    return store


# --- QUEUE_SPIKE ------------------------------------------------------------


def test_queue_spike_triggers_above_threshold(monkeypatch) -> None:
    fresh = MemoryStore()
    fresh.last_queue_depth_by_store["S1"] = 8
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)
    result = detect_anomalies("S1", queue_spike_threshold=5, now=datetime(2026, 1, 1, tzinfo=UTC))
    types = [a.anomaly_type for a in result]
    assert "QUEUE_SPIKE" in types


def test_queue_spike_suppressed_below_threshold(monkeypatch) -> None:
    fresh = MemoryStore()
    fresh.last_queue_depth_by_store["S2"] = 3
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)
    result = detect_anomalies("S2", queue_spike_threshold=5, now=datetime(2026, 1, 1, tzinfo=UTC))
    assert all(a.anomaly_type != "QUEUE_SPIKE" for a in result)


def test_queue_spike_severity_levels() -> None:
    from app.services.anomaly_service import _queue_severity
    assert _queue_severity(10, 5) == "critical"   # ratio 2.0
    assert _queue_severity(8, 5) == "high"         # ratio 1.6
    assert _queue_severity(6, 5) == "medium"       # ratio 1.2


# --- CONVERSION_DROP --------------------------------------------------------


def test_conversion_drop_triggers_with_enough_visitors(monkeypatch) -> None:
    """10 visitors, 0 conversions → below default 5% threshold."""
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    sid_base = "S3"
    for i in range(10):
        vid = f"V-{i:04d}"
        sess = f"{sid_base}-{vid}"
        ev = _base_event(sid_base, "ENTRY", vid, sess, payload={"entry_point": "front", "confidence": 0.9})
        # insert directly
        from pipeline.schemas import parse_event
        parsed = parse_event(ev)
        fresh.insert_event(parsed, ev.get("payload", {}))

    result = detect_anomalies(
        sid_base,
        conversion_drop_threshold=0.05,
        conversion_min_visitors=10,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    types = [a.anomaly_type for a in result]
    assert "CONVERSION_DROP" in types


def test_conversion_drop_suppressed_below_min_visitors(monkeypatch) -> None:
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    result = detect_anomalies(
        "S4",
        conversion_drop_threshold=0.05,
        conversion_min_visitors=10,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert all(a.anomaly_type != "CONVERSION_DROP" for a in result)


def test_conversion_drop_suppressed_when_rate_meets_threshold(monkeypatch) -> None:
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    # 2 of 10 visitors converted = 20% > 5% threshold
    from pipeline.schemas import parse_event
    for i in range(10):
        vid = f"V-{i:04d}"
        sess = f"S5-{vid}"
        ev = _base_event("S5", "ENTRY", vid, sess, payload={"entry_point": "front", "confidence": 0.9})
        parsed = parse_event(ev)
        fresh.insert_event(parsed, ev.get("payload", {}))
        if i < 2:
            fresh.sessions[sess].converted = True

    result = detect_anomalies(
        "S5",
        conversion_drop_threshold=0.05,
        conversion_min_visitors=10,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert all(a.anomaly_type != "CONVERSION_DROP" for a in result)


# --- DEAD_ZONE --------------------------------------------------------------


def test_dead_zone_triggers_when_zones_have_no_dwell(monkeypatch) -> None:
    fresh = _fresh_store_with_layout("S6")
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    from pipeline.schemas import parse_event
    # Add 5 visitors with no dwell events
    for i in range(5):
        vid = f"V-{i:04d}"
        sess = f"S6-{vid}"
        ev = _base_event("S6", "ENTRY", vid, sess, payload={"entry_point": "front", "confidence": 0.9})
        parsed = parse_event(ev)
        fresh.insert_event(parsed, ev.get("payload", {}))

    result = detect_anomalies(
        "S6",
        dead_zone_min_visitors=5,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    types = [a.anomaly_type for a in result]
    assert "DEAD_ZONE" in types
    dead_record = next(a for a in result if a.anomaly_type == "DEAD_ZONE")
    # Both layout zones should be dead
    assert "FOH" in dead_record.context["dead_zone_ids"]
    assert "SKINCARE" in dead_record.context["dead_zone_ids"]


def test_dead_zone_suppressed_when_zones_have_dwell(monkeypatch) -> None:
    fresh = _fresh_store_with_layout("S7")
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    from pipeline.schemas import parse_event
    for i in range(5):
        vid = f"V-{i:04d}"
        sess = f"S7-{vid}"
        # ENTRY
        ev_entry = _base_event("S7", "ENTRY", vid, sess, payload={"entry_point": "front", "confidence": 0.9})
        fresh.insert_event(parse_event(ev_entry), ev_entry.get("payload", {}))
        # ZONE_DWELL for both zones
        for zone in ("FOH", "SKINCARE"):
            ev_dwell = _base_event(
                "S7", "ZONE_DWELL", vid, sess,
                zone_id=zone,
                payload={"zone_name": zone, "dwell_seconds": 30},
                offset=60,
            )
            fresh.insert_event(parse_event(ev_dwell), ev_dwell.get("payload", {}))

    result = detect_anomalies(
        "S7",
        dead_zone_min_visitors=5,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert all(a.anomaly_type != "DEAD_ZONE" for a in result)


def test_dead_zone_suppressed_when_no_layout(monkeypatch) -> None:
    fresh = MemoryStore()  # no layout registered
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    from pipeline.schemas import parse_event
    for i in range(5):
        vid = f"V-{i:04d}"
        ev = _base_event("S8", "ENTRY", vid, f"S8-{vid}", payload={"entry_point": "front", "confidence": 0.9})
        fresh.insert_event(parse_event(ev), ev.get("payload", {}))

    result = detect_anomalies("S8", dead_zone_min_visitors=5, now=datetime(2026, 1, 1, tzinfo=UTC))
    assert all(a.anomaly_type != "DEAD_ZONE" for a in result)


# --- STALE_FEED -------------------------------------------------------------


def test_stale_feed_triggers_after_threshold(monkeypatch) -> None:
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    last_event_time = datetime(2026, 4, 10, 10, 0, 0, tzinfo=UTC)
    fresh._last_event_ts_by_store["S9"] = last_event_time

    now = last_event_time + timedelta(seconds=400)  # 400s > 300s threshold
    result = detect_anomalies("S9", stale_feed_seconds=300, now=now)
    types = [a.anomaly_type for a in result]
    assert "STALE_FEED" in types
    stale = next(a for a in result if a.anomaly_type == "STALE_FEED")
    assert stale.severity == "high"
    assert stale.context["age_seconds"] == 400


def test_stale_feed_suppressed_when_recent(monkeypatch) -> None:
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    last_event_time = datetime(2026, 4, 10, 10, 0, 0, tzinfo=UTC)
    fresh._last_event_ts_by_store["S10"] = last_event_time

    now = last_event_time + timedelta(seconds=100)  # 100s < 300s threshold
    result = detect_anomalies("S10", stale_feed_seconds=300, now=now)
    assert all(a.anomaly_type != "STALE_FEED" for a in result)


def test_stale_feed_suppressed_when_no_events_yet(monkeypatch) -> None:
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.anomaly_service.MEMORY_STORE", fresh)

    result = detect_anomalies("S11", stale_feed_seconds=300, now=datetime(2026, 1, 1, tzinfo=UTC))
    assert all(a.anomaly_type != "STALE_FEED" for a in result)


# --- API endpoint integration -----------------------------------------------


def test_anomalies_endpoint_returns_list() -> None:
    """The endpoint must always return a valid AnomaliesResponse."""
    resp = client.get("/stores/ST_UNKNOWN/anomalies")
    assert resp.status_code == 200
    body = resp.json()
    assert "store_id" in body
    assert isinstance(body["anomalies"], list)


def test_anomalies_endpoint_queue_spike_via_ingest() -> None:
    """Ingesting BILLING_QUEUE_JOIN events with high depth surfaces a QUEUE_SPIKE."""
    store_id = "ST_ANOM_TEST"
    events_batch = []
    for i in range(3):
        vid = f"VA-{i:04d}"
        sess = f"{store_id}-{vid}"
        events_batch.append(
            _base_event(store_id, "ENTRY", vid, sess, offset=i, payload={"entry_point": "front", "confidence": 0.9})
        )
        events_batch.append(
            _base_event(
                store_id,
                "BILLING_QUEUE_JOIN",
                vid,
                sess,
                zone_id="BILLING_QUEUE",
                offset=i + 10,
                payload={"queue_depth": 8},
            )
        )

    _ingest(events_batch)

    resp = client.get(f"/stores/{store_id}/anomalies")
    assert resp.status_code == 200
    body = resp.json()
    types = [a["anomaly_type"] for a in body["anomalies"]]
    assert "QUEUE_SPIKE" in types
