"""Event ingest service."""

from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from app.models.api import IngestError, IngestResponse
from app.repositories.memory import MEMORY_STORE
from pipeline.schemas import BaseEvent, parse_event


def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate a DetectionEvent (pipeline wire format) into the BaseEvent
    format expected by parse_event / the ingest API.

    DetectionEvent fields:
        event_id, store_id, camera_id, visitor_id, event_type,
        timestamp, zone_id, dwell_ms, is_staff, confidence, metadata

    BaseEvent fields:
        event_id, store_id, visitor_id, session_id, event_type,
        event_ts, camera_id, zone_id, payload, idempotency_key
    """
    # Already in BaseEvent format if it has event_ts
    if "event_ts" in raw:
        return raw

    normalized = dict(raw)

    # timestamp -> event_ts
    if "timestamp" in normalized and "event_ts" not in normalized:
        normalized["event_ts"] = normalized.pop("timestamp")

    # session_id: derive from visitor_id (one session per visitor for now)
    if "session_id" not in normalized:
        normalized["session_id"] = f"SES_{normalized.get('visitor_id', 'unknown')}"

    # idempotency_key: use event_id if present, else generate
    if "idempotency_key" not in normalized:
        normalized["idempotency_key"] = str(normalized.get("event_id", uuid4()))

    # payload: build from fields that belong in the payload
    if "payload" not in normalized:
        payload: Dict[str, Any] = {}
        metadata = normalized.get("metadata", {})

        etype = normalized.get("event_type", "")

        if etype == "ZONE_DWELL":
            dwell_ms = normalized.get("dwell_ms", 0)
            payload["dwell_seconds"] = max(1, int(dwell_ms) // 1000)
            payload["zone_name"] = normalized.get("zone_id")

        elif etype in ("ZONE_ENTER", "ZONE_EXIT"):
            payload["zone_name"] = normalized.get("zone_id")

        elif etype == "BILLING_QUEUE_JOIN":
            payload["queue_depth"] = int(metadata.get("queue_depth", 1))

        elif etype == "BILLING_QUEUE_ABANDON":
            payload["queue_depth"] = int(metadata.get("queue_depth", 0))
            payload["wait_seconds"] = int(metadata.get("wait_seconds", 0))

        elif etype == "REENTRY":
            payload["gap_seconds"] = int(metadata.get("gap_seconds", 0))
            payload["match_confidence"] = float(
                normalized.get("confidence", 1.0)
            )

        normalized["payload"] = payload

    return normalized


def ingest_events(events: List[Dict[str, Any]]) -> IngestResponse:
    accepted = 0
    errors: List[IngestError] = []

    for index, raw in enumerate(events):
        try:
            normalized = _normalize_event(raw)
            event: BaseEvent = parse_event(normalized)
        except Exception as exc:  # noqa: BLE001
            errors.append(IngestError(index=index, message=str(exc)))
            continue

        payload_dict = normalized.get("payload", {})
        if not isinstance(payload_dict, dict):
            # payload may already be a Pydantic model after parse_event
            payload_dict = {}

        stored = MEMORY_STORE.insert_event(event, payload_dict)
        if stored:
            accepted += 1

    rejected = len(events) - accepted
    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)
