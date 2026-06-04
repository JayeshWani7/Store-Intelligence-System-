"""In-memory repository used for Phase 4 endpoint scaffolding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pipeline.layout import Layout
from pipeline.schemas import BaseEvent, EventType


@dataclass
class SessionRecord:
    session_id: str
    store_id: str
    visitor_id: str
    entry_ts: datetime
    last_event_ts: datetime
    status: str = "active"
    exit_ts: Optional[datetime] = None
    converted: bool = False
    conversion_order_id: Optional[str] = None
    conversion_ts: Optional[datetime] = None
    dwell_seconds: Optional[int] = None
    billing_queue_seconds: Optional[int] = None
    zone_dwell_seconds: Dict[str, int] = field(default_factory=dict)
    queue_joined: bool = False
    queue_abandoned: bool = False


class MemoryStore:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self.sessions: Dict[str, SessionRecord] = {}
        self.idempotency_keys: Set[str] = set()
        self.last_queue_depth_by_store: Dict[str, int] = {}
        self._layouts: Dict[str, Layout] = {}
        self._last_event_ts_by_store: Dict[str, datetime] = {}

    def register_layout(self, store_id: str, layout: Layout) -> None:
        """Register a store layout for anomaly detection zone checks."""
        self._layouts[store_id] = layout

    def get_layout(self, store_id: str) -> Optional[Layout]:
        return self._layouts.get(store_id)

    def get_last_event_ts(self, store_id: str) -> Optional[datetime]:
        return self._last_event_ts_by_store.get(store_id)

    def insert_event(self, event: BaseEvent, raw_payload: Dict[str, Any]) -> bool:
        if event.idempotency_key in self.idempotency_keys:
            return False

        self.idempotency_keys.add(event.idempotency_key)
        self.events.append({
            "event": event,
            "payload": raw_payload,
        })

        prev_ts = self._last_event_ts_by_store.get(event.store_id)
        if prev_ts is None or event.event_ts > prev_ts:
            self._last_event_ts_by_store[event.store_id] = event.event_ts

        session = self.sessions.get(event.session_id)
        if session is None:
            session = SessionRecord(
                session_id=event.session_id,
                store_id=event.store_id,
                visitor_id=event.visitor_id,
                entry_ts=event.event_ts,
                last_event_ts=event.event_ts,
            )
            self.sessions[event.session_id] = session

        session.last_event_ts = max(session.last_event_ts, event.event_ts)

        if event.event_type == EventType.ENTRY:
            session.entry_ts = event.event_ts
            session.status = "active"

        elif event.event_type == EventType.EXIT:
            session.exit_ts = event.event_ts
            session.status = "closed"
            session.dwell_seconds = max(
                0, int((event.event_ts - session.entry_ts).total_seconds())
            )

        elif event.event_type == EventType.REENTRY:
            session.status = "active"

        elif event.event_type == EventType.ZONE_DWELL:
            zone_key = event.zone_id or raw_payload.get("zone_name") or "UNKNOWN"
            dwell_seconds = raw_payload.get("dwell_seconds", 0)
            session.zone_dwell_seconds[zone_key] = (
                session.zone_dwell_seconds.get(zone_key, 0) + int(dwell_seconds)
            )

        elif event.event_type == EventType.BILLING_QUEUE_JOIN:
            session.queue_joined = True
            queue_depth = raw_payload.get("queue_depth", 0)
            self.last_queue_depth_by_store[event.store_id] = int(queue_depth)

        elif event.event_type == EventType.BILLING_QUEUE_ABANDON:
            session.queue_abandoned = True
            wait_seconds = int(raw_payload.get("wait_seconds", 0))
            session.billing_queue_seconds = (
                (session.billing_queue_seconds or 0) + wait_seconds
            )
            queue_depth = raw_payload.get("queue_depth", 0)
            self.last_queue_depth_by_store[event.store_id] = int(queue_depth)

        if raw_payload.get("converted") or raw_payload.get("conversion_order_id"):
            session.converted = True
            session.conversion_order_id = raw_payload.get("conversion_order_id")
            conversion_ts = raw_payload.get("conversion_ts")
            if isinstance(conversion_ts, datetime):
                session.conversion_ts = conversion_ts

        return True

    def get_sessions_by_store(self, store_id: str) -> List[SessionRecord]:
        return [s for s in self.sessions.values() if s.store_id == store_id]

    def get_events_by_store(self, store_id: str) -> List[BaseEvent]:
        return [item["event"] for item in self.events if item["event"].store_id == store_id]

    def get_queue_depth(self, store_id: str) -> int:
        return self.last_queue_depth_by_store.get(store_id, 0)


MEMORY_STORE = MemoryStore()
