# erd.md

# Entity Relationship Diagram

```mermaid
erDiagram
  stores {
    text store_id PK
    text store_name
    text city
  }

  events {
    uuid event_id PK
    text store_id FK
    text visitor_id
    text session_id
    text event_type
    timestamptz event_ts
    text camera_id
    text zone_id
    jsonb payload
    text idempotency_key
    timestamptz created_at
  }

  sessions {
    text session_id PK
    text store_id FK
    text visitor_id
    timestamptz entry_ts
    timestamptz exit_ts
    boolean converted
    text conversion_order_id
    timestamptz conversion_ts
    integer dwell_seconds
    integer billing_queue_seconds
    timestamptz last_event_ts
    text status
    jsonb metadata
    timestamptz created_at
    timestamptz updated_at
  }

  session_zones {
    uuid session_zone_id PK
    text session_id FK
    text zone_id
    timestamptz enter_ts
    timestamptz exit_ts
    integer dwell_seconds
  }

  anomalies {
    uuid anomaly_id PK
    text store_id FK
    text anomaly_type
    text severity
    timestamptz detected_ts
    text window_start
    text window_end
    jsonb context
    text status
    timestamptz created_at
  }

  metrics_snapshots {
    uuid snapshot_id PK
    text store_id FK
    date business_date
    timestamptz window_start
    timestamptz window_end
    integer unique_visitors
    integer converted_visitors
    numeric conversion_rate
    numeric avg_dwell_seconds
    numeric avg_queue_seconds
    numeric abandonment_rate
    jsonb zone_heatmap
    timestamptz created_at
  }

  idempotency_keys {
    text idempotency_key PK
    timestamptz first_seen
    text source
  }

  stores ||--o{ events : contains
  stores ||--o{ sessions : has
  sessions ||--o{ session_zones : includes
  stores ||--o{ anomalies : reports
  stores ||--o{ metrics_snapshots : aggregates
  sessions ||--o{ events : emits
