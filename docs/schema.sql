-- schema.sql
-- Phase 2: PostgreSQL core tables and indexes

CREATE TABLE IF NOT EXISTS stores (
  store_id TEXT PRIMARY KEY,
  store_name TEXT NOT NULL,
  city TEXT
);

CREATE TABLE IF NOT EXISTS events (
  event_id UUID PRIMARY KEY,
  store_id TEXT NOT NULL REFERENCES stores(store_id),
  visitor_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_ts TIMESTAMPTZ NOT NULL,
  camera_id TEXT,
  zone_id TEXT,
  payload JSONB NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  store_id TEXT NOT NULL REFERENCES stores(store_id),
  visitor_id TEXT NOT NULL,
  entry_ts TIMESTAMPTZ NOT NULL,
  exit_ts TIMESTAMPTZ,
  converted BOOLEAN NOT NULL DEFAULT FALSE,
  conversion_order_id TEXT,
  conversion_ts TIMESTAMPTZ,
  dwell_seconds INTEGER,
  billing_queue_seconds INTEGER,
  last_event_ts TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_zones (
  session_zone_id UUID PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  zone_id TEXT NOT NULL,
  enter_ts TIMESTAMPTZ NOT NULL,
  exit_ts TIMESTAMPTZ,
  dwell_seconds INTEGER
);

CREATE TABLE IF NOT EXISTS anomalies (
  anomaly_id UUID PRIMARY KEY,
  store_id TEXT NOT NULL REFERENCES stores(store_id),
  anomaly_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  detected_ts TIMESTAMPTZ NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metrics_snapshots (
  snapshot_id UUID PRIMARY KEY,
  store_id TEXT NOT NULL REFERENCES stores(store_id),
  business_date DATE NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  window_end TIMESTAMPTZ NOT NULL,
  unique_visitors INTEGER NOT NULL,
  converted_visitors INTEGER NOT NULL,
  conversion_rate NUMERIC(6,4) NOT NULL,
  avg_dwell_seconds NUMERIC(10,2),
  avg_queue_seconds NUMERIC(10,2),
  abandonment_rate NUMERIC(6,4),
  zone_heatmap JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  idempotency_key TEXT PRIMARY KEY,
  first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source TEXT
);

CREATE INDEX IF NOT EXISTS events_store_ts_idx ON events(store_id, event_ts);
CREATE INDEX IF NOT EXISTS events_store_type_ts_idx ON events(store_id, event_type, event_ts);
CREATE INDEX IF NOT EXISTS events_session_ts_idx ON events(session_id, event_ts);

CREATE INDEX IF NOT EXISTS sessions_store_status_ts_idx ON sessions(store_id, status, last_event_ts);
CREATE INDEX IF NOT EXISTS sessions_store_entry_ts_idx ON sessions(store_id, entry_ts);
CREATE INDEX IF NOT EXISTS sessions_store_converted_idx ON sessions(store_id, converted);
CREATE INDEX IF NOT EXISTS sessions_visitor_store_idx ON sessions(visitor_id, store_id);

CREATE INDEX IF NOT EXISTS session_zones_session_zone_idx ON session_zones(session_id, zone_id);
CREATE INDEX IF NOT EXISTS session_zones_zone_enter_idx ON session_zones(zone_id, enter_ts);

CREATE INDEX IF NOT EXISTS anomalies_store_detected_idx ON anomalies(store_id, detected_ts);
CREATE INDEX IF NOT EXISTS anomalies_store_type_idx ON anomalies(store_id, anomaly_type);
CREATE INDEX IF NOT EXISTS anomalies_status_detected_idx ON anomalies(status, detected_ts);

CREATE INDEX IF NOT EXISTS metrics_store_date_idx ON metrics_snapshots(store_id, business_date);
CREATE INDEX IF NOT EXISTS metrics_store_window_idx ON metrics_snapshots(store_id, window_start);
