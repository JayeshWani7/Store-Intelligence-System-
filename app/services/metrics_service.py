"""Metrics aggregation service (in-memory for Phase 4)."""

from __future__ import annotations

from typing import Dict

from app.repositories.memory import MEMORY_STORE
from pipeline.schemas import EventType


def get_metrics(store_id: str) -> Dict[str, object]:
    sessions = MEMORY_STORE.get_sessions_by_store(store_id)
    unique_visitors = len({s.visitor_id for s in sessions})
    converted_visitors = len([s for s in sessions if s.converted])
    conversion_rate = (
        converted_visitors / unique_visitors if unique_visitors > 0 else 0.0
    )

    dwell_values = [s.dwell_seconds for s in sessions if s.dwell_seconds is not None]
    avg_dwell_seconds = (
        sum(dwell_values) / len(dwell_values) if dwell_values else None
    )

    queue_values = [
        s.billing_queue_seconds
        for s in sessions
        if s.billing_queue_seconds is not None
    ]
    avg_queue_seconds = (
        sum(queue_values) / len(queue_values) if queue_values else None
    )

    queue_joined = len([s for s in sessions if s.queue_joined])
    queue_abandoned = len([s for s in sessions if s.queue_abandoned])
    abandonment_rate = (
        queue_abandoned / queue_joined if queue_joined > 0 else None
    )

    zone_heatmap: Dict[str, int] = {}
    for session in sessions:
        for zone_id, dwell in session.zone_dwell_seconds.items():
            zone_heatmap[zone_id] = zone_heatmap.get(zone_id, 0) + dwell

    return {
        "unique_visitors": unique_visitors,
        "converted_visitors": converted_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_seconds": avg_dwell_seconds,
        "avg_queue_seconds": avg_queue_seconds,
        "abandonment_rate": abandonment_rate,
        "queue_depth": MEMORY_STORE.get_queue_depth(store_id),
        "zone_heatmap": zone_heatmap,
    }


def get_funnel(store_id: str) -> Dict[str, int]:
    events = MEMORY_STORE.get_events_by_store(store_id)
    entry_count = len([e for e in events if e.event_type == EventType.ENTRY])
    zone_entry_count = len([e for e in events if e.event_type == EventType.ZONE_ENTER])
    queue_join_count = len(
        [e for e in events if e.event_type == EventType.BILLING_QUEUE_JOIN]
    )
    exit_count = len([e for e in events if e.event_type == EventType.EXIT])
    converted_count = len(
        [s for s in MEMORY_STORE.get_sessions_by_store(store_id) if s.converted]
    )

    return {
        "entry_count": entry_count,
        "zone_entry_count": zone_entry_count,
        "queue_join_count": queue_join_count,
        "converted_count": converted_count,
        "exit_count": exit_count,
    }


def get_heatmap(store_id: str) -> Dict[str, int]:
    return get_metrics(store_id)["zone_heatmap"]
