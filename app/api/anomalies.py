"""Anomalies endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import AnomaliesResponse
from app.services.anomaly_service import detect_anomalies

router = APIRouter()


@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
def anomalies(store_id: str) -> AnomaliesResponse:
    active = detect_anomalies(store_id)
    return AnomaliesResponse(store_id=store_id, anomalies=active)
