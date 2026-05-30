"""Funnel endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.api import FunnelResponse
from app.services.metrics_service import get_funnel

router = APIRouter()


@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
def funnel(store_id: str) -> FunnelResponse:
    data = get_funnel(store_id)
    return FunnelResponse(store_id=store_id, **data)
