"""Health endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.models.api import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", db="not_configured", redis="not_configured")
