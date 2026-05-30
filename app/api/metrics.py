"""Metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import MetricsResponse
from app.services.metrics_service import get_metrics

router = APIRouter()


@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
def metrics(store_id: str) -> MetricsResponse:
    data = get_metrics(store_id)
    return MetricsResponse(store_id=store_id, **data)
