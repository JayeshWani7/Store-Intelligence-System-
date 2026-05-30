# architecture.md

# Store Intelligence Architecture

## North Star

Conversion Rate = Converted Visitors / Unique Visitors

Every component exists to improve conversion analytics accuracy, explainability, and reliability.

---

## System Data Flow

Raw CCTV -> Detection -> Tracking -> Re-ID -> Event Generation -> Redis Streams -> Ingest API -> PostgreSQL -> Metrics Engine -> API Responses -> Dashboard

---

## Pipeline Modules

### pipeline/detect.py

- Responsibility: run YOLOv8s person detection on frames
- Inputs: video frames
- Outputs: detections with bbox, confidence
- Dependencies: YOLOv8s runtime, GPU optional

### pipeline/tracker.py

- Responsibility: assign consistent track IDs across frames (ByteTrack)
- Inputs: detections per frame
- Outputs: tracked objects with track_id, bbox
- Dependencies: ByteTrack, frame timestamps

### pipeline/reid.py

- Responsibility: identify returning visitors and cross-camera matches (OSNet)
- Inputs: tracked crops, embeddings
- Outputs: identity matches with confidence
- Dependencies: OSNet model weights, embedding store

### pipeline/emit.py

- Responsibility: convert vision signals into business events
- Inputs: tracks, identity matches, zone mapping
- Outputs: event objects ready for ingestion
- Dependencies: event schemas, zone definitions

### pipeline/schemas.py

- Responsibility: shared event and signal schemas
- Inputs: schema definitions
- Outputs: Pydantic models, validators
- Dependencies: pydantic

### pipeline/run.py

- Responsibility: orchestrate end-to-end pipeline loop
- Inputs: stream config, camera sources
- Outputs: event stream push
- Dependencies: detect, tracker, reid, emit

---

## API Modules

### app/main.py

- Responsibility: FastAPI app assembly, routing, middleware
- Inputs: configuration
- Outputs: API server
- Dependencies: FastAPI, routers

### app/api/

- Responsibility: HTTP endpoints for ingest, metrics, funnel, heatmap, anomalies, health
- Inputs: request payloads
- Outputs: responses
- Dependencies: services, models

### app/services/

- Responsibility: business logic for ingest, sessions, metrics
- Inputs: validated events, store context
- Outputs: write operations and aggregates
- Dependencies: repositories, models

### app/repositories/

- Responsibility: data access for PostgreSQL and Redis
- Inputs: queries, commands
- Outputs: persisted entities, stream consumption
- Dependencies: async db driver, redis client

### app/models/

- Responsibility: Pydantic and DB models for events, sessions, metrics
- Inputs: schema definitions
- Outputs: validated data objects
- Dependencies: pydantic

### app/consumers/

- Responsibility: Redis Streams consumption, idempotency, retry handling
- Inputs: stream entries
- Outputs: stored events, processed acknowledgements
- Dependencies: redis, repositories

### app/metrics/

- Responsibility: session-based aggregation for conversion analytics
- Inputs: events and sessions
- Outputs: metrics results
- Dependencies: repositories

### app/anomalies/

- Responsibility: rule-based anomaly detection
- Inputs: metrics time series
- Outputs: anomaly records
- Dependencies: metrics engine

### app/health/

- Responsibility: health checks for DB, Redis, event freshness
- Inputs: service status
- Outputs: health report
- Dependencies: repositories

---

## Data Dependencies

- PostgreSQL: events, sessions, metrics snapshots, anomalies
- Redis Streams: event buffering for reliability
- Object storage: optional for raw video references

---

## Reliability Strategy

- Redis Streams decouples event generation from persistence
- Idempotency keys prevent double counting
- Session-based aggregation avoids expensive replays
- Health checks expose data freshness and connectivity
