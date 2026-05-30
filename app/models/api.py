"""API request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)


class IngestError(BaseModel):
    index: int
    message: str


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[IngestError] = Field(default_factory=list)


class MetricsResponse(BaseModel):
    store_id: str
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    unique_visitors: int
    converted_visitors: int
    conversion_rate: float
    avg_dwell_seconds: Optional[float] = None
    avg_queue_seconds: Optional[float] = None
    abandonment_rate: Optional[float] = None
    queue_depth: int = 0
    zone_heatmap: Dict[str, int] = Field(default_factory=dict)


class FunnelResponse(BaseModel):
    store_id: str
    entry_count: int
    zone_entry_count: int
    queue_join_count: int
    converted_count: int
    exit_count: int


class HeatmapResponse(BaseModel):
    store_id: str
    zone_heatmap: Dict[str, int] = Field(default_factory=dict)


class AnomalyRecord(BaseModel):
    anomaly_type: str
    severity: str
    detected_ts: datetime
    status: str
    context: Dict[str, Any] = Field(default_factory=dict)


class AnomaliesResponse(BaseModel):
    store_id: str
    anomalies: List[AnomalyRecord] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    event_freshness_seconds: Optional[int] = None
