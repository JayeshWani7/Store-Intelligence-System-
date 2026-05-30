"""Anomalies endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.models.api import AnomaliesResponse

router = APIRouter()


@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
def anomalies(store_id: str) -> AnomaliesResponse:
    return AnomaliesResponse(store_id=store_id, anomalies=[])
