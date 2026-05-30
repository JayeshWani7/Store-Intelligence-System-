"""Pydantic schemas for event validation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional, Type
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, conint, confloat, field_validator


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ZONE_ENTER = "ZONE_ENTER"
    ZONE_EXIT = "ZONE_EXIT"
    ZONE_DWELL = "ZONE_DWELL"
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_ABANDON = "BILLING_QUEUE_ABANDON"
    REENTRY = "REENTRY"


class EntryPayload(BaseModel):
    entry_point: Optional[str] = None
    confidence: Optional[confloat(ge=0.0, le=1.0)] = None
    model_config = ConfigDict(extra="ignore")


class ExitPayload(BaseModel):
    exit_point: Optional[str] = None
    confidence: Optional[confloat(ge=0.0, le=1.0)] = None
    model_config = ConfigDict(extra="ignore")


class ZonePayload(BaseModel):
    zone_name: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class ZoneDwellPayload(BaseModel):
    zone_name: Optional[str] = None
    dwell_seconds: conint(ge=0)
    model_config = ConfigDict(extra="ignore")


class BillingQueueJoinPayload(BaseModel):
    queue_depth: conint(ge=0)
    model_config = ConfigDict(extra="ignore")


class BillingQueueAbandonPayload(BaseModel):
    queue_depth: conint(ge=0)
    wait_seconds: conint(ge=0)
    model_config = ConfigDict(extra="ignore")


class ReentryPayload(BaseModel):
    gap_seconds: conint(ge=0)
    match_confidence: confloat(ge=0.0, le=1.0)
    model_config = ConfigDict(extra="ignore")


class BaseEvent(BaseModel):
    event_id: UUID
    store_id: str
    visitor_id: str
    session_id: str
    event_type: EventType
    event_ts: datetime
    camera_id: Optional[str] = None
    zone_id: Optional[str] = None
    payload: Dict[str, Any]
    idempotency_key: str
    model_config = ConfigDict(extra="ignore")

    @field_validator("store_id", "visitor_id", "session_id", "idempotency_key")
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be non-empty")
        return value


class EntryEvent(BaseEvent):
    event_type: Literal[EventType.ENTRY] = Field(default=EventType.ENTRY)
    payload: EntryPayload


class ExitEvent(BaseEvent):
    event_type: Literal[EventType.EXIT] = Field(default=EventType.EXIT)
    payload: ExitPayload


class ZoneEnterEvent(BaseEvent):
    event_type: Literal[EventType.ZONE_ENTER] = Field(default=EventType.ZONE_ENTER)
    payload: ZonePayload


class ZoneExitEvent(BaseEvent):
    event_type: Literal[EventType.ZONE_EXIT] = Field(default=EventType.ZONE_EXIT)
    payload: ZonePayload


class ZoneDwellEvent(BaseEvent):
    event_type: Literal[EventType.ZONE_DWELL] = Field(default=EventType.ZONE_DWELL)
    payload: ZoneDwellPayload


class BillingQueueJoinEvent(BaseEvent):
    event_type: Literal[EventType.BILLING_QUEUE_JOIN] = Field(
        default=EventType.BILLING_QUEUE_JOIN
    )
    payload: BillingQueueJoinPayload


class BillingQueueAbandonEvent(BaseEvent):
    event_type: Literal[EventType.BILLING_QUEUE_ABANDON] = Field(
        default=EventType.BILLING_QUEUE_ABANDON
    )
    payload: BillingQueueAbandonPayload


class ReentryEvent(BaseEvent):
    event_type: Literal[EventType.REENTRY] = Field(default=EventType.REENTRY)
    payload: ReentryPayload


EVENT_MODEL_BY_TYPE: Dict[EventType, Type[BaseEvent]] = {
    EventType.ENTRY: EntryEvent,
    EventType.EXIT: ExitEvent,
    EventType.ZONE_ENTER: ZoneEnterEvent,
    EventType.ZONE_EXIT: ZoneExitEvent,
    EventType.ZONE_DWELL: ZoneDwellEvent,
    EventType.BILLING_QUEUE_JOIN: BillingQueueJoinEvent,
    EventType.BILLING_QUEUE_ABANDON: BillingQueueAbandonEvent,
    EventType.REENTRY: ReentryEvent,
}


def parse_event(data: Dict[str, Any]) -> BaseEvent:
    """Validate and parse an event payload into the correct event model."""

    event_type = data.get("event_type")
    if not event_type:
        raise ValueError("event_type is required")

    try:
        event_type_enum = EventType(event_type)
    except ValueError as exc:
        raise ValueError(f"Unsupported event_type: {event_type}") from exc

    model = EVENT_MODEL_BY_TYPE[event_type_enum]
    return model.model_validate(data)
