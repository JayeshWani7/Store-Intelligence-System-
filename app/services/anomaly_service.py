"""Rule-based anomaly detection engine.

Four rules are evaluated on each call:

- QUEUE_SPIKE       Queue depth exceeds threshold.
- CONVERSION_DROP   Conversion rate falls below threshold after a minimum
                    number of visitors have passed through.
- DEAD_ZONE         A floor or brand zone has received zero dwell in the
                    observation window despite visitors being present.
- STALE_FEED        No events have been ingested for the store in the last
                    N seconds, which may indicate a camera or pipeline failure.

All thresholds are configurable via keyword arguments so tests and callers
can override them without patching module-level constants.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.api import AnomalyRecord
from app.repositories.memory import MEMORY_STORE
from pipeline.schemas import EventType

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

QUEUE_SPIKE_THRESHOLD: int = 5          # persons in queue
CONVERSION_DROP_THRESHOLD: float = 0.05  # 5 % conversion rate
CONVERSION_MIN_VISITORS: int = 10        # ignore when too few data points
STALE_FEED_SECONDS: int = 300            # 5 minutes without any event
DEAD_ZONE_MIN_VISITORS: int = 5          # need this many visitors before flagging

# Zone types that are expected to attract dwell; entry/queue/billing excluded.
_DWELL_EXPECTED_ZONE_TYPES = {"floor", "brand", "fixture"}


def detect_anomalies(
    store_id: str,
    *,
    queue_spike_threshold: int = QUEUE_SPIKE_THRESHOLD,
    conversion_drop_threshold: float = CONVERSION_DROP_THRESHOLD,
    conversion_min_visitors: int = CONVERSION_MIN_VISITORS,
    stale_feed_seconds: int = STALE_FEED_SECONDS,
    dead_zone_min_visitors: int = DEAD_ZONE_MIN_VISITORS,
    now: Optional[datetime] = None,
) -> List[AnomalyRecord]:
    """Evaluate all rules and return a list of active anomaly records."""

    if now is None:
        now = datetime.now(tz=timezone.utc)

    anomalies: List[AnomalyRecord] = []

    anomalies.extend(
        _rule_queue_spike(store_id, threshold=queue_spike_threshold, now=now)
    )
    anomalies.extend(
        _rule_conversion_drop(
            store_id,
            threshold=conversion_drop_threshold,
            min_visitors=conversion_min_visitors,
            now=now,
        )
    )
    anomalies.extend(
        _rule_dead_zone(
            store_id,
            min_visitors=dead_zone_min_visitors,
            now=now,
        )
    )
    anomalies.extend(
        _rule_stale_feed(store_id, stale_seconds=stale_feed_seconds, now=now)
    )

    return anomalies


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------


def _rule_queue_spike(
    store_id: str,
    threshold: int,
    now: datetime,
) -> List[AnomalyRecord]:
    """Trigger when current queue depth exceeds the threshold."""

    depth = MEMORY_STORE.get_queue_depth(store_id)
    if depth < threshold:
        return []

    return [
        AnomalyRecord(
            anomaly_type="QUEUE_SPIKE",
            severity=_queue_severity(depth, threshold),
            detected_ts=now,
            status="active",
            context={
                "queue_depth": depth,
                "threshold": threshold,
                "reason": (
                    f"Billing queue depth {depth} exceeds threshold {threshold}. "
                    "Consider opening an additional counter."
                ),
            },
        )
    ]


def _rule_conversion_drop(
    store_id: str,
    threshold: float,
    min_visitors: int,
    now: datetime,
) -> List[AnomalyRecord]:
    """Trigger when conversion rate is below threshold with sufficient data."""

    sessions = MEMORY_STORE.get_sessions_by_store(store_id)
    unique_visitors = len({s.visitor_id for s in sessions})

    if unique_visitors < min_visitors:
        return []

    converted = len([s for s in sessions if s.converted])
    rate = converted / unique_visitors

    if rate >= threshold:
        return []

    return [
        AnomalyRecord(
            anomaly_type="CONVERSION_DROP",
            severity="high" if rate == 0.0 else "medium",
            detected_ts=now,
            status="active",
            context={
                "conversion_rate": round(rate, 4),
                "threshold": threshold,
                "unique_visitors": unique_visitors,
                "converted_visitors": converted,
                "reason": (
                    f"Conversion rate {rate:.1%} is below threshold {threshold:.1%} "
                    f"across {unique_visitors} visitors."
                ),
            },
        )
    ]


def _rule_dead_zone(
    store_id: str,
    min_visitors: int,
    now: datetime,
) -> List[AnomalyRecord]:
    """Flag zones that expected dwell traffic but have received none."""

    sessions = MEMORY_STORE.get_sessions_by_store(store_id)
    unique_visitors = len({s.visitor_id for s in sessions})

    if unique_visitors < min_visitors:
        return []

    # Build set of zone IDs that have any recorded dwell
    zones_with_dwell = set()
    for session in sessions:
        zones_with_dwell.update(session.zone_dwell_seconds.keys())

    # Find which zones should have dwell but don't
    layout = MEMORY_STORE.get_layout(store_id)
    if layout is None:
        return []

    dead_zones = [
        zone
        for zone in layout.zones
        if zone.zone_type in _DWELL_EXPECTED_ZONE_TYPES
        and zone.zone_id not in zones_with_dwell
    ]

    if not dead_zones:
        return []

    return [
        AnomalyRecord(
            anomaly_type="DEAD_ZONE",
            severity="low",
            detected_ts=now,
            status="active",
            context={
                "dead_zone_ids": [z.zone_id for z in dead_zones],
                "dead_zone_labels": [z.label for z in dead_zones],
                "unique_visitors": unique_visitors,
                "reason": (
                    f"{len(dead_zones)} zone(s) recorded zero dwell despite "
                    f"{unique_visitors} visitors in the store."
                ),
            },
        )
    ]


def _rule_stale_feed(
    store_id: str,
    stale_seconds: int,
    now: datetime,
) -> List[AnomalyRecord]:
    """Trigger when no events have arrived in the last stale_seconds."""

    last_ts = MEMORY_STORE.get_last_event_ts(store_id)
    if last_ts is None:
        # No events yet — not a feed failure, just an empty store.
        return []

    age_seconds = int((now - last_ts).total_seconds())
    if age_seconds <= stale_seconds:
        return []

    return [
        AnomalyRecord(
            anomaly_type="STALE_FEED",
            severity="high",
            detected_ts=now,
            status="active",
            context={
                "last_event_ts": last_ts.isoformat(),
                "age_seconds": age_seconds,
                "threshold_seconds": stale_seconds,
                "reason": (
                    f"No events received for {age_seconds}s "
                    f"(threshold {stale_seconds}s). "
                    "Camera or pipeline failure may have occurred."
                ),
            },
        )
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _queue_severity(depth: int, threshold: int) -> str:
    ratio = depth / max(threshold, 1)
    if ratio >= 2.0:
        return "critical"
    if ratio >= 1.5:
        return "high"
    return "medium"
