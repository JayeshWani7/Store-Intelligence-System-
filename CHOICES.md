# CHOICES.md — Engineering Decision Records

## Purplle Store Intelligence Challenge

This document records the major engineering decisions made while building the Store Intelligence platform.

The goal of this document is not to prove that every decision is optimal.

The goal is to explain why specific tradeoffs were made under the constraints of:

* 48 hour implementation window
* Limited compute resources
* Unknown evaluation hardware
* Real-time analytics requirements
* Production-readiness expectations

---

# ADR-001: Detection Model Selection

## Decision

Use **YOLOv8s** as the primary person detection model.

---

## Context

The challenge requires processing:

* 1080p CCTV footage
* 15 FPS
* 3 camera streams per store

The business objective is not object detection accuracy.

The business objective is accurate visitor analytics.

This distinction matters because not every detection error affects the business equally.

A missed detection near the entrance directly impacts visitor count and conversion rate.

A missed detection in a product zone may only affect dwell calculations.

Therefore the model was evaluated primarily on its ability to consistently detect people entering and exiting the store.

---

## Alternatives Considered

### YOLOv8n

Pros:

* Extremely fast
* Low memory usage
* Easy deployment

Cons:

* Missed partially occluded visitors more frequently
* Less reliable in crowded billing areas

---

### RT-DETR

Pros:

* Strong detection quality
* Better handling of occlusions

Cons:

* Higher inference latency
* More deployment complexity
* Less mature ecosystem

---

### YOLOv11

Pros:

* Newer architecture
* Slightly improved benchmark performance

Cons:

* Smaller ecosystem
* Fewer examples and integrations
* No meaningful improvement for challenge objectives

---

## AI Recommendation

Claude initially recommended RT-DETR because of its stronger benchmark accuracy.

After introducing deployment and latency constraints, the recommendation shifted toward YOLOv8s.

---

## Evaluation

I deliberately stopped optimizing once detection quality became "good enough" for conversion analytics.

The challenge evaluates business outcomes, not benchmark leaderboards.

The additional complexity of RT-DETR did not materially improve the metrics that matter:

* Visitor count
* Conversion rate
* Queue monitoring

---

## Final Choice

YOLOv8s

---

## Consequences

Benefits:

* Fast inference
* Mature tooling
* Simple deployment

Costs:

* Some detection loss during heavy occlusion
* Slightly lower accuracy than transformer-based alternatives

Accepted tradeoff.

---

# ADR-002: Tracking and Re-Identification

## Decision

Use:

* ByteTrack for tracking
* OSNet for Re-ID

---

## Context

Tracking and Re-ID solve different problems.

Tracking answers:

"Is this the same person between consecutive frames?"

Re-ID answers:

"Is this the same person after leaving the camera view?"

Attempting to solve both with one system produced weaker results during experimentation.

---

## Alternatives Considered

### DeepSORT

Pros:

* Well understood
* Easy setup

Cons:

* Track fragmentation during occlusion
* Sensitive to confidence fluctuations

---

### StrongSORT

Pros:

* Better appearance matching
* Better re-association

Cons:

* Slower
* More complex
* Additional computation cost

---

### ByteTrack

Pros:

* Fast
* Handles low confidence detections well
* Easy to reason about

Cons:

* Does not solve cross-camera identity

---

## AI Recommendation

GPT suggested StrongSORT initially.

After discussing throughput requirements and multi-camera deployment, ByteTrack plus a separate Re-ID component became the recommended architecture.

---

## What Changed During Development

My first implementation used DeepSORT.

It worked adequately in simple scenes.

Problems appeared in the billing area where multiple customers frequently overlapped.

Rather than continuing to tune DeepSORT parameters, I switched to ByteTrack.

The resulting failure modes became easier to understand and debug.

---

## Final Choice

ByteTrack + OSNet

---

## Consequences

Benefits:

* Better track continuity
* Faster execution
* Clear separation of responsibilities

Costs:

* Re-ID remains the largest source of uncertainty
* Re-entry handling is probabilistic rather than deterministic

Accepted tradeoff.

---

# ADR-003: Event Schema Design

## Decision

Use a denormalized event schema.

---

## Context

The event schema is consumed by:

* Metrics API
* Funnel calculations
* Dashboard
* Future analytics systems

I wanted every event to be independently understandable.

---

## Alternatives Considered

### Fully Normalized Schema

Pros:

* Reduced storage duplication
* Cleaner relational design

Cons:

* More joins
* Harder debugging
* Slower analytics queries

---

### Denormalized Schema

Pros:

* Self-contained events
* Simpler analytics
* Easier debugging

Cons:

* Repeated metadata

---

## AI Recommendation

AI suggested a CQRS architecture with event sourcing.

The recommendation was technically sound.

However it introduced complexity that did not materially improve challenge outcomes.

---

## Why I Rejected Full CQRS

I have implemented CQRS systems before.

For this challenge it would have increased:

* Infrastructure
* Debugging effort
* Operational complexity

without improving reviewer-facing functionality.

The evaluator spends a limited amount of time reviewing submissions.

I optimized for correctness and explainability rather than architectural completeness.

---

## Final Choice

Denormalized events with append-only storage.

---

# ADR-004: Database Selection

## Decision

PostgreSQL

---

## Context

The dataset itself is small.

Storage capacity was not the deciding factor.

Operational flexibility was.

---

## Alternatives Considered

### SQLite

Pros:

* Single file
* Very simple deployment
* Fewer moving parts

Cons:

* Concurrency limitations
* Harder future scaling

---

### PostgreSQL

Pros:

* Better concurrent ingestion
* JSONB support
* Better observability
* Materialized views

Cons:

* Additional container
* Slightly more operational overhead

---

## Why PostgreSQL Won

The challenge dataset could comfortably fit into SQLite.

The reason I chose PostgreSQL was not scale.

It was realism.

Every additional feature:

* Session tracking
* Materialized views
* Health monitoring
* Concurrent ingestion

became easier to implement cleanly.

If this were purely a prototype, SQLite would likely be my choice.

---

## Final Choice

PostgreSQL

---

# ADR-005: Why I Stopped Optimizing

## Observation

A common engineering mistake is continuing optimization after business requirements are already satisfied.

I consciously avoided this.

---

## Examples

I could have:

* Switched to RT-DETR
* Implemented CQRS
* Added Kafka
* Added distributed tracing
* Added ML-based anomaly detection

All of these would make the architecture more impressive.

None would significantly improve the accuracy of conversion analytics for this challenge.

---

## Decision

Once visitor counting, funnel calculations, and conversion metrics were producing reliable results, I shifted effort toward:

* Reliability
* Documentation
* Testing
* Operational visibility

rather than architectural expansion.

---

## Final Reflection

The biggest technical challenge was not object detection.

It was maintaining visitor identity across:

* Occlusions
* Camera transitions
* Re-entry events

Most analytics errors originate from identity failures rather than detection failures.

Given another week, improving Re-ID quality would deliver more business value than replacing the detector with a more advanced model.
