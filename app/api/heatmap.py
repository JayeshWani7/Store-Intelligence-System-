"""Heatmap endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import HeatmapResponse
from app.services.metrics_service import get_heatmap

router = APIRouter()


@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
def heatmap(store_id: str) -> HeatmapResponse:
    zone_heatmap = get_heatmap(store_id)
    return HeatmapResponse(store_id=store_id, zone_heatmap=zone_heatmap)
