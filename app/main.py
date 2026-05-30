"""FastAPI app entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from app.api import anomalies, events, funnel, health, heatmap, metrics

app = FastAPI(title="Store Intelligence API", version="0.1.0")

app.include_router(events.router)
app.include_router(metrics.router)
app.include_router(funnel.router)
app.include_router(heatmap.router)
app.include_router(anomalies.router)
app.include_router(health.router)
