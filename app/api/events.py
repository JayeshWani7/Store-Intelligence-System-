"""Event ingest endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.api import IngestRequest, IngestResponse
from app.services.ingest_service import ingest_events

router = APIRouter()


@router.post("/events/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    if not request.events:
        raise HTTPException(status_code=400, detail="events must not be empty")
    return ingest_events(request.events)
