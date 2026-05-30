# database-schema.md

# Database Schema Design (Phase 2)

## Goals

- Preserve raw events for auditability
- Maintain session state for fast metrics
- Support idempotent ingestion
- Keep queries simple and explainable

---

## Tables

### stores

- Purpose: store reference data
- Key fields:
  - store_id (PK)
  - store_name
  - city

### events

- Purpose: append-only event log
- Key fields:
  - event_id (UUID, PK)
  - store_id (FK -> stores)
  - visitor_id (string, from re-id)
  - session_id (string)
  - event_type (enum string)
  - event_ts (timestamptz)
  - camera_id (string)
  - zone_id (string)
  - payload (jsonb)
  - idempotency_key (string, unique)
  - created_at (timestamptz)

### sessions

- Purpose: active and closed visitor sessions
- Key fields:
  - session_id (PK)
  - store_id (FK -> stores)
  - visitor_id
  - entry_ts
  - exit_ts
  - converted (boolean)
  - conversion_order_id (string, nullable)
  - conversion_ts (timestamptz, nullable)
  - dwell_seconds (int, derived)
  - billing_queue_seconds (int, derived)
  - last_event_ts
  - status (active|closed|abandoned)
  - metadata (jsonb)
  - created_at, updated_at

### session_zones

- Purpose: track per-zone dwell without replaying events
- Key fields:
  - session_zone_id (UUID, PK)
  - session_id (FK -> sessions)
  - zone_id
  - enter_ts
  - exit_ts
  - dwell_seconds

### anomalies

- Purpose: rule-based anomaly records
- Key fields:
  - anomaly_id (UUID, PK)
  - store_id (FK -> stores)
  - anomaly_type (queue_spike|conversion_drop|dead_zone|stale_feed)
  - severity (low|medium|high)
  - detected_ts
  - window_start, window_end
  - context (jsonb)
  - status (open|acknowledged|resolved)
  - created_at

### metrics_snapshots

- Purpose: precomputed metrics for fast reads
- Key fields:
  - snapshot_id (UUID, PK)
  - store_id (FK -> stores)
  - business_date
  - window_start, window_end
  - unique_visitors
  - converted_visitors
  - conversion_rate
  - avg_dwell_seconds
  - avg_queue_seconds
  - abandonment_rate
  - zone_heatmap (jsonb)
  - created_at

### idempotency_keys

- Purpose: guard against duplicate ingestion
- Key fields:
  - idempotency_key (PK)
  - first_seen
  - source

---

## Indexes

### events

- (store_id, event_ts) for time-range queries
- (store_id, event_type, event_ts) for metrics aggregation
- (session_id, event_ts) for session reconstruction
- (idempotency_key) unique

### sessions

- (store_id, status, last_event_ts)
- (store_id, entry_ts)
- (store_id, converted)
- (visitor_id, store_id)

### session_zones

- (session_id, zone_id)
- (zone_id, enter_ts)

### anomalies

- (store_id, detected_ts)
- (store_id, anomaly_type)
- (status, detected_ts)

### metrics_snapshots

- (store_id, business_date)
- (store_id, window_start)

---

## Session Model

### Session Identity

- session_id = store_id + visitor_id + first_entry_ts
- session is opened on ENTRY
- session closes on EXIT or inactivity timeout
- re-entry within 30 minutes reuses session_id and emits REENTRY

### Session State Rules

- entry_ts set on first ENTRY
- exit_ts set on EXIT or timeout
- converted set only after POS correlation
- conversion_order_id and conversion_ts set from POS event
- dwell_seconds derived from entry_ts to exit_ts
- billing_queue_seconds derived from billing queue events

---

## Event Model

### Required Events

- ENTRY
- EXIT
- ZONE_ENTER
- ZONE_EXIT
- ZONE_DWELL
- BILLING_QUEUE_JOIN
- BILLING_QUEUE_ABANDON
- REENTRY

### Common Event Fields

- event_id
- store_id
- visitor_id
- session_id
- event_type
- event_ts
- camera_id
- zone_id (optional)
- payload (event-specific details)
- idempotency_key

### Event-Specific Payloads

- ENTRY: {"entry_point": "front", "confidence": 0.93}
- EXIT: {"exit_point": "front", "confidence": 0.91}
- ZONE_ENTER: {"zone_name": "SKINCARE"}
- ZONE_EXIT: {"zone_name": "SKINCARE"}
- ZONE_DWELL: {"zone_name": "SKINCARE", "dwell_seconds": 30}
- BILLING_QUEUE_JOIN: {"queue_depth": 3}
- BILLING_QUEUE_ABANDON: {"queue_depth": 2, "wait_seconds": 95}
- REENTRY: {"gap_seconds": 420, "match_confidence": 0.86}

---

## Notes

- events is append-only; updates happen in sessions and metrics_snapshots
- payload uses jsonb for flexibility while keeping core fields indexed
- idempotency_key can be generated from event source + event_id
