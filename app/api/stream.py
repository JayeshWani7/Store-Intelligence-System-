"""Server-Sent Events endpoint for live metric streaming."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.anomaly_service import detect_anomalies
from app.services.metrics_service import get_funnel, get_metrics

router = APIRouter()


async def _event_stream(store_id: str, interval: float = 3.0) -> AsyncIterator[str]:
    """Yield SSE frames with metrics, funnel, and anomalies on each tick."""
    while True:
        try:
            metrics = get_metrics(store_id)
            funnel = get_funnel(store_id)
            anomalies = [
                {
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "detected_ts": a.detected_ts.isoformat(),
                    "status": a.status,
                    "context": a.context,
                }
                for a in detect_anomalies(store_id)
            ]

            payload = {
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "store_id": store_id,
                "metrics": {
                    k: v
                    for k, v in metrics.items()
                    if k != "zone_heatmap"
                },
                "zone_heatmap": metrics.get("zone_heatmap", {}),
                "funnel": funnel,
                "anomalies": anomalies,
            }
            yield f"data: {json.dumps(payload)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        await asyncio.sleep(interval)


@router.get("/stores/{store_id}/stream")
async def stream(store_id: str, interval: float = 3.0) -> StreamingResponse:
    """Stream live store metrics as Server-Sent Events."""
    return StreamingResponse(
        _event_stream(store_id, interval=max(1.0, interval)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
