"""FastAPI app entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import anomalies, events, funnel, health, heatmap, metrics, stream
from app.repositories.memory import MEMORY_STORE
from pipeline.layout import load_layout


@asynccontextmanager
async def lifespan(app: FastAPI):
    layout_path = os.environ.get("STORE_LAYOUT_PATH", "store_layout.json")
    try:
        layout = load_layout(layout_path)
        MEMORY_STORE.register_layout(layout.store_id, layout)
    except Exception:  # noqa: BLE001
        pass
    yield


app = FastAPI(title="Store Intelligence API", version="0.1.0", lifespan=lifespan)


_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(metrics.router)
app.include_router(funnel.router)
app.include_router(heatmap.router)
app.include_router(anomalies.router)
app.include_router(health.router)
app.include_router(stream.router)
