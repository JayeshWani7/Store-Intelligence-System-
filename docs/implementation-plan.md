# implementation-plan.md

# Implementation Roadmap

## Fastest Path To >85

- Ship acceptance gates first: docker compose, event ingest, metrics endpoint
- Keep pipeline minimal: emit valid events even if video ingestion is mocked
- Prioritize session-based conversion correctness over model tuning
- Defer dashboard and anomalies until API and metrics stabilize
- Produce tests per endpoint to improve reviewer confidence

---

## Phase 1

### What will be built

- Folder structure
- architecture.md
- implementation-plan.md
- technical-decision-log.md

### Why it exists

- Establishes clarity and reviewer confidence

### Risks

- Misalignment with required structure

### Dependencies

- None

### Acceptance criteria

- Folder tree matches required layout
- Docs describe modules, inputs, outputs, dependencies

---

## Phase 2

### What will be built

- ERD
- PostgreSQL schema for events, sessions, anomalies
- Index plan

### Why it exists

- Enables correct conversion analytics and fast reads

### Risks

- Over-normalized tables make metrics slow

### Dependencies

- Phase 1 architecture

### Acceptance criteria

- Tables and indexes cover ingestion and metrics queries

---

## Phase 3

### What will be built

- Pydantic event models
- Validation rules
- Sample payloads

### Why it exists

- Ensures ingestion correctness and schema stability

### Risks

- Missing validation lets bad events corrupt sessions

### Dependencies

- Phase 2 schema

### Acceptance criteria

- All required event types validate
- Sample payloads cover core and edge cases

---

## Phase 4

### What will be built

- FastAPI endpoints
- Tests, curl examples, sample responses per endpoint

### Why it exists

- Required acceptance gates and reviewer visibility

### Risks

- Metrics endpoint depends on session logic correctness

### Dependencies

- Phase 2 and Phase 3

### Acceptance criteria

- POST /events/ingest works
- GET /stores/{id}/metrics works
- Health endpoint returns service status

---

## Phase 5

### What will be built

- Redis Streams ingestion pipeline
- Idempotency and retry handling
- Structured logging

### Why it exists

- Prevents event loss during restarts

### Risks

- Duplicate processing if idempotency is weak

### Dependencies

- Phase 4 ingest endpoint

### Acceptance criteria

- Replaying the same event does not change metrics

---

## Phase 6

### What will be built

- Session-based metrics engine
- Aggregates: unique visitors, conversion rate, avg dwell, queue depth, abandonment rate

### Why it exists

- Core business value for conversion analytics

### Risks

- Re-entry logic errors skew conversion rate

### Dependencies

- Phases 2 to 5

### Acceptance criteria

- Metrics stable across replays
- Handles empty store and zero purchases

---

## Phase 7

### What will be built

- Rule-based anomaly detection
- Rules: queue spike, conversion drop, dead zone, stale feed

### Why it exists

- Operational visibility without ML complexity

### Risks

- False positives from naive thresholds

### Dependencies

- Phase 6 metrics

### Acceptance criteria

- Deterministic rule triggers with clear reasons

---

## Phase 8

### What will be built

- Minimal React + Vite dashboard
- SSE updates for live metrics

### Why it exists

- Reviewer visibility and completeness

### Risks

- Time sink if started before API stability

### Dependencies

- Phases 4 and 7

### Acceptance criteria

- Dashboard loads on clean machine and streams updates

---

## Phase 9

### What will be built

- pytest suite targeting >70% coverage
- Scenarios: re-entry, duplicates, empty store, all staff, zero purchases

### Why it exists

- Confidence in correctness

### Risks

- Brittle tests if schemas shift late

### Dependencies

- Phases 3 to 8

### Acceptance criteria

- Coverage target achieved
- All required scenarios passing

---

## Phase 10

### What will be built

- DESIGN.md
- CHOICES.md
- ASSUMPTIONS.md
- RISKS.md
- LEARNINGS.md
- FOLLOWUP_PREP.md

### Why it exists

- Defendable decisions during follow-up interviews

### Risks

- Docs drift from implementation if written too early

### Dependencies

- Phases 1 to 9

### Acceptance criteria

- Docs consistent with the final implementation
