"""Event ingest service."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.models.api import IngestError, IngestResponse
from app.repositories.memory import MEMORY_STORE
from pipeline.schemas import BaseEvent, parse_event


def ingest_events(events: List[Dict[str, Any]]) -> IngestResponse:
    accepted = 0
    errors: List[IngestError] = []

    for index, raw in enumerate(events):
        try:
            event: BaseEvent = parse_event(raw)
        except Exception as exc:  # noqa: BLE001
            errors.append(IngestError(index=index, message=str(exc)))
            continue

        stored = MEMORY_STORE.insert_event(event, raw.get("payload", {}))
        if stored:
            accepted += 1

    rejected = len(events) - accepted
    return IngestResponse(accepted=accepted, rejected=rejected, errors=errors)
