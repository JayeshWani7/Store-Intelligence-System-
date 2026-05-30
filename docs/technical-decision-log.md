# technical-decision-log.md

# Technical Decision Log

This log captures the most important implementation decisions and the reasoning behind them.

---

## TD-001 Detector: YOLOv8s

- Decision: Use YOLOv8s for person detection
- Rationale: Good enough accuracy for conversion analytics with lower latency and mature tooling
- Alternatives: YOLOv8n, RT-DETR, YOLOv11
- Impact: Faster inference, simpler deployment

---

## TD-002 Tracking: ByteTrack

- Decision: Use ByteTrack for tracking
- Rationale: Stable tracking under occlusion, handles low-confidence detections
- Alternatives: DeepSORT, StrongSORT
- Impact: Fewer track fragments, simpler tuning

---

## TD-003 Re-ID: OSNet

- Decision: Use OSNet for re-identification
- Rationale: Balanced accuracy and speed for appearance matching
- Alternatives: Stronger re-ID backbones with higher compute cost
- Impact: Enables re-entry handling and cross-camera continuity

---

## TD-004 Storage: PostgreSQL

- Decision: Store events, sessions, and aggregates in PostgreSQL
- Rationale: Strong transactional semantics, JSONB support, easy observability
- Alternatives: SQLite
- Impact: Better concurrency, more realistic production posture

---

## TD-005 Event Buffering: Redis Streams

- Decision: Buffer events in Redis Streams
- Rationale: Avoid event loss during restarts and transient DB errors
- Alternatives: Direct DB writes, Kafka
- Impact: Improved reliability without heavy infrastructure

---

## TD-006 Event Model: Denormalized Events

- Decision: Store events in a denormalized schema
- Rationale: Faster analytics queries, easier debugging
- Alternatives: Fully normalized schema
- Impact: Slightly higher storage, lower query complexity

---

## TD-007 Aggregation: Session-Based Metrics

- Decision: Use session tables and incremental updates
- Rationale: Avoid expensive full event replays for metrics
- Alternatives: Pure event sourcing
- Impact: Faster API responses, simpler operational model

---

## TD-008 API Framework: FastAPI

- Decision: FastAPI for ingestion and metrics endpoints
- Rationale: Async-friendly, strong typing with Pydantic
- Alternatives: Flask, Django
- Impact: Faster iteration and clear validation

---

## TD-009 Dashboard Transport: SSE

- Decision: Use server-sent events for updates
- Rationale: Simple, reliable for low-frequency metrics updates
- Alternatives: WebSockets
- Impact: Lower operational complexity

---

## TD-010 Testing: pytest

- Decision: pytest for unit and integration tests
- Rationale: Industry standard, fast feedback loops
- Alternatives: unittest
- Impact: Better test readability and fixtures
