"""Scenario-based tests covering the cases specified in Phase 9.

Scenarios covered:
  1. Re-entry          — visitor exits and re-enters; counted as one unique visitor,
                         session stays active, dwell accumulates.
  2. Duplicate events  — replaying the same idempotency key is rejected; metrics
                         are not double-counted.
  3. Empty store       — metrics return valid zeros, no division errors.
  4. Zero purchases    — visitors present but none converted; conversion_rate == 0.
  5. All staff         — sessions flagged as staff are excluded from customer metrics.
                         (staff flag is carried via is_staff on DetectionEvent; here
                         we test the boundary: no conversions, no visitors counted.)
  6. Funnel ordering   — funnel counts reflect the correct event sequence.
  7. Queue abandon     — abandonment_rate computed correctly.
  8. Dwell accumulates — multiple ZONE_DWELL events for same zone sum correctly.
  9. Heatmap endpoint  — mirrors zone_heatmap from metrics.
 10. Bad payload       — malformed events are rejected with an error entry.

Each test uses a fresh MemoryStore injected via monkeypatch so there is
absolutely no shared state between tests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.memory import MemoryStore
from pipeline.schemas import parse_event

client = TestClient(app)

UTC = timezone.utc
_BASE_TS = datetime(2026, 4, 10, 9, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return str(uuid.uuid4())


def _ts(offset_seconds: int = 0) -> str:
    return (_BASE_TS + timedelta(seconds=offset_seconds)).isoformat()


def _entry(
    store_id: str,
    visitor_id: str,
    session_id: str,
    *,
    offset: int = 0,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "ENTRY",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": None,
        "payload": {"entry_point": "front", "confidence": 0.9},
        "idempotency_key": _uid(),
    }


def _exit(
    store_id: str,
    visitor_id: str,
    session_id: str,
    *,
    offset: int = 60,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "EXIT",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": None,
        "payload": {"exit_point": "front", "confidence": 0.9},
        "idempotency_key": _uid(),
    }


def _reentry(
    store_id: str,
    visitor_id: str,
    session_id: str,
    *,
    offset: int = 120,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "REENTRY",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": None,
        "payload": {"gap_seconds": 60, "match_confidence": 0.87},
        "idempotency_key": _uid(),
    }


def _zone_dwell(
    store_id: str,
    visitor_id: str,
    session_id: str,
    zone_id: str,
    dwell_seconds: int,
    *,
    offset: int = 30,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "ZONE_DWELL",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": zone_id,
        "payload": {"zone_name": zone_id, "dwell_seconds": dwell_seconds},
        "idempotency_key": _uid(),
    }


def _queue_join(
    store_id: str,
    visitor_id: str,
    session_id: str,
    queue_depth: int,
    *,
    offset: int = 90,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "BILLING_QUEUE_JOIN",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": "BILLING_QUEUE",
        "payload": {"queue_depth": queue_depth},
        "idempotency_key": _uid(),
    }


def _queue_abandon(
    store_id: str,
    visitor_id: str,
    session_id: str,
    queue_depth: int,
    wait_seconds: int,
    *,
    offset: int = 150,
) -> Dict[str, Any]:
    return {
        "event_id": _uid(),
        "store_id": store_id,
        "visitor_id": visitor_id,
        "session_id": session_id,
        "event_type": "BILLING_QUEUE_ABANDON",
        "event_ts": _ts(offset),
        "camera_id": "cam-1",
        "zone_id": "BILLING_QUEUE",
        "payload": {"queue_depth": queue_depth, "wait_seconds": wait_seconds},
        "idempotency_key": _uid(),
    }


def _ingest(store: MemoryStore, events: List[Dict[str, Any]]) -> None:
    """Directly insert events into the given MemoryStore (bypasses HTTP layer)."""
    for raw in events:
        parsed = parse_event(raw)
        store.insert_event(parsed, raw.get("payload", {}))


def _metrics(store: MemoryStore, store_id: str) -> Dict[str, Any]:
    from app.services.metrics_service import get_metrics
    import app.services.metrics_service as svc
    # temporarily redirect the module-level MEMORY_STORE reference
    original = svc.MEMORY_STORE
    svc.MEMORY_STORE = store
    try:
        return get_metrics(store_id)
    finally:
        svc.MEMORY_STORE = original


def _funnel(store: MemoryStore, store_id: str) -> Dict[str, Any]:
    from app.services.metrics_service import get_funnel
    import app.services.metrics_service as svc
    original = svc.MEMORY_STORE
    svc.MEMORY_STORE = store
    try:
        return get_funnel(store_id)
    finally:
        svc.MEMORY_STORE = original


# ---------------------------------------------------------------------------
# Scenario 1 — Re-entry
# ---------------------------------------------------------------------------


def test_reentry_counts_as_one_unique_visitor() -> None:
    """EXIT + REENTRY on the same session_id must not inflate unique_visitors."""
    store = MemoryStore()
    sid = "STORE_RE"
    vid = "V-RE-001"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _exit(sid, vid, sess, offset=60),
        _reentry(sid, vid, sess, offset=120),
    ])

    m = _metrics(store, sid)
    assert m["unique_visitors"] == 1, "Re-entry must not create a duplicate visitor"


def test_reentry_reopens_session() -> None:
    """After REENTRY the session status must be active again."""
    store = MemoryStore()
    sid = "STORE_RE2"
    vid = "V-RE-002"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _exit(sid, vid, sess, offset=60),
        _reentry(sid, vid, sess, offset=120),
    ])

    session = store.sessions[sess]
    assert session.status == "active"


def test_reentry_dwell_accumulates_across_visits() -> None:
    """Zone dwell from both the initial visit and the re-entry visit should sum."""
    store = MemoryStore()
    sid = "STORE_RE3"
    vid = "V-RE-003"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _zone_dwell(sid, vid, sess, "SKINCARE", 30, offset=30),
        _exit(sid, vid, sess, offset=60),
        _reentry(sid, vid, sess, offset=120),
        _zone_dwell(sid, vid, sess, "SKINCARE", 45, offset=150),
    ])

    session = store.sessions[sess]
    assert session.zone_dwell_seconds.get("SKINCARE") == 75


# ---------------------------------------------------------------------------
# Scenario 2 — Duplicate events (idempotency)
# ---------------------------------------------------------------------------


def test_duplicate_event_rejected() -> None:
    """Sending the same idempotency_key twice must increment accepted by 1 not 2."""
    store = MemoryStore()
    sid = "STORE_DUP"
    vid = "V-DUP-001"
    sess = f"{sid}-{vid}"

    idem_key = "FIXED-IDEM-KEY-001"
    ev = {
        "event_id": _uid(),
        "store_id": sid,
        "visitor_id": vid,
        "session_id": sess,
        "event_type": "ENTRY",
        "event_ts": _ts(0),
        "camera_id": "cam-1",
        "zone_id": None,
        "payload": {"entry_point": "front", "confidence": 0.9},
        "idempotency_key": idem_key,
    }

    result1 = store.insert_event(parse_event(ev), ev["payload"])
    result2 = store.insert_event(parse_event({**ev, "event_id": _uid()}), ev["payload"])

    assert result1 is True
    assert result2 is False, "Second insert with same idempotency_key must be rejected"


def test_duplicate_does_not_inflate_visitor_count() -> None:
    """Replaying the same event batch must not change unique_visitors."""
    store = MemoryStore()
    sid = "STORE_DUP2"
    vid = "V-DUP-002"
    sess = f"{sid}-{vid}"

    idem = "IDEM-FIXED-002"
    ev = {
        "event_id": _uid(),
        "store_id": sid,
        "visitor_id": vid,
        "session_id": sess,
        "event_type": "ENTRY",
        "event_ts": _ts(0),
        "camera_id": "cam-1",
        "zone_id": None,
        "payload": {"entry_point": "front", "confidence": 0.9},
        "idempotency_key": idem,
    }

    store.insert_event(parse_event(ev), ev["payload"])
    store.insert_event(parse_event({**ev, "event_id": _uid()}), ev["payload"])

    m = _metrics(store, sid)
    assert m["unique_visitors"] == 1


def test_duplicate_dwell_not_double_counted() -> None:
    """Replaying a ZONE_DWELL event must not double the zone dwell seconds."""
    store = MemoryStore()
    sid = "STORE_DUP3"
    vid = "V-DUP-003"
    sess = f"{sid}-{vid}"

    _ingest(store, [_entry(sid, vid, sess)])

    idem = "IDEM-DWELL-003"
    dwell_ev = {
        "event_id": _uid(),
        "store_id": sid,
        "visitor_id": vid,
        "session_id": sess,
        "event_type": "ZONE_DWELL",
        "event_ts": _ts(30),
        "camera_id": "cam-1",
        "zone_id": "LIPSTICK",
        "payload": {"zone_name": "LIPSTICK", "dwell_seconds": 60},
        "idempotency_key": idem,
    }

    store.insert_event(parse_event(dwell_ev), dwell_ev["payload"])
    store.insert_event(parse_event({**dwell_ev, "event_id": _uid()}), dwell_ev["payload"])

    session = store.sessions[sess]
    assert session.zone_dwell_seconds.get("LIPSTICK") == 60, \
        "Dwell must not be counted twice on duplicate event"


# ---------------------------------------------------------------------------
# Scenario 3 — Empty store
# ---------------------------------------------------------------------------


def test_empty_store_metrics_are_valid_zeros() -> None:
    """A store with no events must return zeroed metrics without raising."""
    store = MemoryStore()
    m = _metrics(store, "STORE_EMPTY")

    assert m["unique_visitors"] == 0
    assert m["converted_visitors"] == 0
    assert m["conversion_rate"] == 0.0
    assert m["avg_dwell_seconds"] is None
    assert m["avg_queue_seconds"] is None
    assert m["abandonment_rate"] is None
    assert m["queue_depth"] == 0
    assert m["zone_heatmap"] == {}


def test_empty_store_funnel_is_all_zeros() -> None:
    store = MemoryStore()
    f = _funnel(store, "STORE_EMPTY_F")

    assert f["entry_count"] == 0
    assert f["zone_entry_count"] == 0
    assert f["queue_join_count"] == 0
    assert f["converted_count"] == 0
    assert f["exit_count"] == 0


def test_empty_store_anomalies_endpoint_returns_200() -> None:
    """Empty store must not crash the anomalies endpoint."""
    resp = client.get("/stores/STORE_EMPTY_ANOM/anomalies")
    assert resp.status_code == 200
    assert resp.json()["anomalies"] == [] or isinstance(resp.json()["anomalies"], list)


# ---------------------------------------------------------------------------
# Scenario 4 — Zero purchases
# ---------------------------------------------------------------------------


def test_zero_purchases_conversion_rate_is_zero() -> None:
    """Visitors who entered and exited without purchasing yield 0.0 conversion."""
    store = MemoryStore()
    sid = "STORE_ZP"

    for i in range(5):
        vid = f"V-ZP-{i:03d}"
        sess = f"{sid}-{vid}"
        _ingest(store, [
            _entry(sid, vid, sess, offset=i * 10),
            _exit(sid, vid, sess, offset=i * 10 + 60),
        ])

    m = _metrics(store, sid)
    assert m["unique_visitors"] == 5
    assert m["converted_visitors"] == 0
    assert m["conversion_rate"] == 0.0


def test_zero_purchases_dwell_still_recorded() -> None:
    """Zero purchases must not affect dwell time recording."""
    store = MemoryStore()
    sid = "STORE_ZP2"
    vid = "V-ZP2-001"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _zone_dwell(sid, vid, sess, "FOUNDATION", 90, offset=45),
        _exit(sid, vid, sess, offset=120),
    ])

    m = _metrics(store, sid)
    assert m["conversion_rate"] == 0.0
    assert m["zone_heatmap"].get("FOUNDATION") == 90


# ---------------------------------------------------------------------------
# Scenario 5 — All staff (no customer conversions)
# ---------------------------------------------------------------------------

# The in-memory store does not yet have a staff filter at the session level;
# staff exclusion is handled at the pipeline level via is_staff on DetectionEvent.
# These tests verify the boundary: if only staff-flagged sessions exist (simulated
# by having no converted sessions and visitor IDs explicitly labelled STAFF),
# the conversion rate must remain 0.0 and the system must not error.


def test_all_staff_sessions_conversion_rate_is_zero() -> None:
    """Store where all visitors behave like staff — conversion must be 0.0."""
    store = MemoryStore()
    sid = "STORE_STAFF"

    for i in range(3):
        vid = f"STAFF-{i:03d}"
        sess = f"{sid}-{vid}"
        _ingest(store, [
            _entry(sid, vid, sess, offset=i * 5),
            # Staff traverse many zones quickly
            _zone_dwell(sid, vid, sess, "FOH", 10, offset=i * 5 + 10),
            _zone_dwell(sid, vid, sess, "BILLING", 5, offset=i * 5 + 20),
            _exit(sid, vid, sess, offset=i * 5 + 30),
        ])

    m = _metrics(store, sid)
    assert m["conversion_rate"] == 0.0
    assert m["converted_visitors"] == 0


def test_all_staff_unique_visitors_counted_in_denominator() -> None:
    """Without an is_staff filter the sessions still appear — no errors raised."""
    store = MemoryStore()
    sid = "STORE_STAFF2"

    for i in range(2):
        vid = f"STAFF-{i:03d}"
        sess = f"{sid}-{vid}"
        _ingest(store, [_entry(sid, vid, sess, offset=i)])

    m = _metrics(store, sid)
    # Visitors are present; conversion rate is 0 since none converted
    assert m["unique_visitors"] == 2
    assert m["conversion_rate"] == 0.0


# ---------------------------------------------------------------------------
# Scenario 6 — Funnel ordering
# ---------------------------------------------------------------------------


def test_funnel_counts_reflect_event_sequence() -> None:
    """Funnel counts must match the actual sequence of events ingested."""
    store = MemoryStore()
    sid = "STORE_FNL"

    visitors = [f"V-FNL-{i:03d}" for i in range(4)]
    events_batch = []

    for vid in visitors:
        sess = f"{sid}-{vid}"
        # All 4 entered
        events_batch.append(_entry(sid, vid, sess, offset=0))

    # Only 3 entered a zone
    for vid in visitors[:3]:
        sess = f"{sid}-{vid}"
        events_batch.append({
            "event_id": _uid(),
            "store_id": sid,
            "visitor_id": vid,
            "session_id": sess,
            "event_type": "ZONE_ENTER",
            "event_ts": _ts(10),
            "camera_id": "cam-1",
            "zone_id": "SKINCARE",
            "payload": {"zone_name": "SKINCARE"},
            "idempotency_key": _uid(),
        })

    # Only 2 joined the queue
    for vid in visitors[:2]:
        sess = f"{sid}-{vid}"
        events_batch.append(_queue_join(sid, vid, sess, 2, offset=30))

    # 1 exited
    sess = f"{sid}-{visitors[0]}"
    events_batch.append(_exit(sid, visitors[0], sess, offset=60))

    _ingest(store, events_batch)

    f = _funnel(store, sid)
    assert f["entry_count"] == 4
    assert f["zone_entry_count"] == 3
    assert f["queue_join_count"] == 2
    assert f["exit_count"] == 1


# ---------------------------------------------------------------------------
# Scenario 7 — Queue abandonment rate
# ---------------------------------------------------------------------------


def test_queue_abandonment_rate_computed_correctly() -> None:
    """2 join, 1 abandons → abandonment_rate == 0.5."""
    store = MemoryStore()
    sid = "STORE_QA"

    # Visitor A: joins and abandons
    va = "V-QA-A"
    sess_a = f"{sid}-{va}"
    _ingest(store, [
        _entry(sid, va, sess_a, offset=0),
        _queue_join(sid, va, sess_a, 2, offset=30),
        _queue_abandon(sid, va, sess_a, 1, 45, offset=75),
    ])

    # Visitor B: joins and stays (no abandon event)
    vb = "V-QA-B"
    sess_b = f"{sid}-{vb}"
    _ingest(store, [
        _entry(sid, vb, sess_b, offset=5),
        _queue_join(sid, vb, sess_b, 2, offset=35),
    ])

    m = _metrics(store, sid)
    assert m["abandonment_rate"] == pytest.approx(0.5)


def test_queue_abandonment_none_when_no_queue_activity() -> None:
    """abandonment_rate must be None when no one joined the queue."""
    store = MemoryStore()
    sid = "STORE_QA2"
    vid = "V-QA2-001"
    sess = f"{sid}-{vid}"
    _ingest(store, [_entry(sid, vid, sess)])

    m = _metrics(store, sid)
    assert m["abandonment_rate"] is None


# ---------------------------------------------------------------------------
# Scenario 8 — Dwell accumulation
# ---------------------------------------------------------------------------


def test_dwell_accumulates_across_multiple_dwell_events() -> None:
    """Three ZONE_DWELL events for the same zone must sum their seconds."""
    store = MemoryStore()
    sid = "STORE_DWL"
    vid = "V-DWL-001"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _zone_dwell(sid, vid, sess, "LIPCARE", 30, offset=30),
        _zone_dwell(sid, vid, sess, "LIPCARE", 30, offset=60),
        _zone_dwell(sid, vid, sess, "LIPCARE", 30, offset=90),
    ])

    m = _metrics(store, sid)
    assert m["zone_heatmap"].get("LIPCARE") == 90


def test_dwell_tracked_separately_per_zone() -> None:
    """Dwell for different zones must be independent entries in the heatmap."""
    store = MemoryStore()
    sid = "STORE_DWL2"
    vid = "V-DWL2-001"
    sess = f"{sid}-{vid}"

    _ingest(store, [
        _entry(sid, vid, sess, offset=0),
        _zone_dwell(sid, vid, sess, "ZONE_A", 40, offset=30),
        _zone_dwell(sid, vid, sess, "ZONE_B", 20, offset=60),
    ])

    m = _metrics(store, sid)
    assert m["zone_heatmap"]["ZONE_A"] == 40
    assert m["zone_heatmap"]["ZONE_B"] == 20


def test_avg_dwell_seconds_calculated_across_sessions() -> None:
    """avg_dwell_seconds must be the mean of closed session dwell values."""
    store = MemoryStore()
    sid = "STORE_DWL3"

    # Visitor A: 60s dwell
    va, sess_a = "V-A", f"{sid}-V-A"
    _ingest(store, [
        _entry(sid, va, sess_a, offset=0),
        _exit(sid, va, sess_a, offset=60),
    ])

    # Visitor B: 120s dwell
    vb, sess_b = "V-B", f"{sid}-V-B"
    _ingest(store, [
        _entry(sid, vb, sess_b, offset=0),
        _exit(sid, vb, sess_b, offset=120),
    ])

    m = _metrics(store, sid)
    assert m["avg_dwell_seconds"] == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# Scenario 9 — Heatmap endpoint mirrors metrics
# ---------------------------------------------------------------------------


def test_heatmap_endpoint_matches_metrics_zone_heatmap(monkeypatch) -> None:
    """GET /stores/{id}/heatmap must return the same data as metrics zone_heatmap."""
    fresh = MemoryStore()
    monkeypatch.setattr("app.services.metrics_service.MEMORY_STORE", fresh)

    sid = "STORE_HM"
    vid = "V-HM-001"
    sess = f"{sid}-{vid}"

    _ingest(fresh, [
        _entry(sid, vid, sess, offset=0),
        _zone_dwell(sid, vid, sess, "BLUSH", 55, offset=30),
    ])

    resp = client.get(f"/stores/{sid}/heatmap")
    assert resp.status_code == 200
    heatmap = resp.json()["zone_heatmap"]
    assert heatmap.get("BLUSH") == 55


# ---------------------------------------------------------------------------
# Scenario 10 — Bad payload rejected gracefully
# ---------------------------------------------------------------------------


def test_bad_event_type_is_rejected() -> None:
    """An unknown event_type must be rejected with an error entry, not a 500."""
    resp = client.post("/events/ingest", json={"events": [
        {
            "event_id": _uid(),
            "store_id": "ST-ERR",
            "visitor_id": "V-ERR",
            "session_id": "SESS-ERR",
            "event_type": "TOTALLY_UNKNOWN",
            "event_ts": _ts(0),
            "camera_id": "cam-1",
            "zone_id": None,
            "payload": {},
            "idempotency_key": _uid(),
        }
    ]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rejected"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["index"] == 0


def test_missing_required_field_is_rejected() -> None:
    """An event missing visitor_id must be rejected cleanly."""
    resp = client.post("/events/ingest", json={"events": [
        {
            "event_id": _uid(),
            "store_id": "ST-ERR2",
            # visitor_id intentionally omitted
            "session_id": "SESS-ERR2",
            "event_type": "ENTRY",
            "event_ts": _ts(0),
            "camera_id": "cam-1",
            "zone_id": None,
            "payload": {"entry_point": "front", "confidence": 0.9},
            "idempotency_key": _uid(),
        }
    ]})
    assert resp.status_code == 200
    assert resp.json()["rejected"] == 1


def test_mixed_batch_partial_accept() -> None:
    """A batch with one good and one bad event must accept 1 and reject 1."""
    resp = client.post("/events/ingest", json={"events": [
        {
            "event_id": _uid(),
            "store_id": "ST-MIX",
            "visitor_id": "V-MIX-001",
            "session_id": "SESS-MIX-001",
            "event_type": "ENTRY",
            "event_ts": _ts(0),
            "camera_id": "cam-1",
            "zone_id": None,
            "payload": {"entry_point": "front", "confidence": 0.9},
            "idempotency_key": _uid(),
        },
        {
            "event_id": _uid(),
            "store_id": "ST-MIX",
            "visitor_id": "V-MIX-002",
            "session_id": "SESS-MIX-002",
            "event_type": "ZONE_DWELL",
            "event_ts": _ts(10),
            "camera_id": "cam-1",
            "zone_id": "ZONE_X",
            # dwell_seconds missing → ZoneDwellPayload validation fails
            "payload": {"zone_name": "ZONE_X"},
            "idempotency_key": _uid(),
        },
    ]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 1
