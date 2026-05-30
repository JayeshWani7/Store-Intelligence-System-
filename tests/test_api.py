"""API tests for Phase 4 endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _sample_event(event_type: str, event_id: str) -> dict:
    return {
        "event_id": event_id,
        "store_id": "ST1008",
        "visitor_id": "V-0001",
        "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
        "event_type": event_type,
        "event_ts": "2026-04-10T12:15:05Z",
        "camera_id": "cam-entry-1",
        "zone_id": "ENTRY",
        "payload": {
            "entry_point": "front",
            "confidence": 0.9,
        },
        "idempotency_key": f"{event_id}-k",
    }


def test_ingest_and_metrics() -> None:
    response = client.post(
        "/events/ingest",
        json={
            "events": [
                _sample_event("ENTRY", "9c9bc6c2-8e6f-4f7e-97c5-99d27d9d2f0d"),
                {
                    **_sample_event(
                        "ZONE_DWELL",
                        "f5c1b2f8-4b4e-4f74-8b21-0d73b6bb02d1",
                    ),
                    "zone_id": "SKINCARE",
                    "payload": {"zone_name": "SKINCARE", "dwell_seconds": 30},
                },
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["accepted"] == 2

    metrics = client.get("/stores/ST1008/metrics")
    assert metrics.status_code == 200
    data = metrics.json()
    assert data["unique_visitors"] == 1
    assert data["conversion_rate"] == 0.0
    assert data["zone_heatmap"]["SKINCARE"] == 30


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_rejects_empty() -> None:
    response = client.post("/events/ingest", json={"events": []})
    assert response.status_code == 400
