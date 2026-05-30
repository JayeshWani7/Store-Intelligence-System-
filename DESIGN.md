# DESIGN.md

# Store Intelligence Platform

## Problem Understanding

The challenge is framed as a computer vision problem, but the actual business problem is measuring offline conversion rate.

Online stores know:

* Who visited
* What they viewed
* How long they stayed
* Whether they purchased

Physical stores typically know only the final transaction.

The objective of this system is to reconstruct the customer journey using CCTV footage and POS transactions.

The North Star metric is:

**Conversion Rate = Converted Visitors / Unique Visitors**

Every architectural decision was evaluated against one question:

> Does this improve the accuracy or usefulness of conversion analytics?

---

# Architecture Overview

```text
Raw CCTV Footage
        │
        ▼
Detection Layer
        │
        ▼
Tracking Layer
        │
        ▼
Re-ID Layer
        │
        ▼
Event Generation
        │
        ▼
Event Stream
        │
        ▼
Intelligence API
        │
        ▼
Metrics Engine
        │
        ▼
Dashboard
```

---

## Detection Layer

### Responsibility

Detect people in video frames.

### Input

Video frames.

### Output

```json
{
  "bbox": [],
  "confidence": 0.91
}
```

### Selected Technology

YOLOv8s

### Why

The goal is not maximum benchmark accuracy.

The goal is reliable visitor counting.

YOLOv8s provided a good balance between:

* Accuracy
* Latency
* Simplicity
* Deployment reliability

### Failure Modes

* Heavy occlusion
* Crowd overlap
* Poor lighting

---

## Tracking Layer

### Responsibility

Maintain identity across consecutive frames.

### Selected Technology

ByteTrack

### Why

Tracking failures create larger downstream errors than detection failures.

A missed detection may affect dwell calculations.

A broken track can create:

* Duplicate visitors
* Broken funnels
* Incorrect conversion attribution

ByteTrack performed more reliably during customer overlap scenarios than my initial DeepSORT implementation.

### Failure Modes

* ID switching
* Long occlusions
* Crowded queues

---

## Re-Identification Layer

### Responsibility

Maintain visitor identity:

* Across cameras
* Across temporary disappearances
* Across re-entry events

### Selected Technology

OSNet

### Why

The biggest challenge in this project was not detecting people.

It was deciding whether two observations belonged to the same person.

Without Re-ID:

* Re-entry becomes impossible
* Cross-camera journeys break
* Visitor counts inflate

### Failure Modes

* Similar clothing
* Clothing changes
* Poor crops

### Known Limitation

Re-ID remains the least reliable component in the system.

If I had another week, this is where I would invest most engineering effort.

---

## Event Generation Layer

### Responsibility

Transform vision signals into business events.

### Example

Raw Detection:

```json
{
  "track_id": 42
}
```

Business Event:

```json
{
  "event_type": "ZONE_ENTER",
  "zone_id": "SKINCARE"
}
```

### Why It Exists

Retail teams care about:

* Dwell
* Conversion
* Queueing

not bounding boxes.

This layer translates technical observations into business language.

---

## Event Streaming Layer

### Responsibility

Decouple event production from event consumption.

### Initial Design

Originally events were written directly to PostgreSQL.

That worked.

The weakness appeared when restarting services during testing.

Events generated during startup windows could be lost.

### Final Design

Redis Streams was introduced to buffer events.

Important:

Redis was added for reliability, not scale.

The challenge dataset is small enough that direct database writes would be acceptable.

### Tradeoff

Pros:

* Improved resilience
* Decoupled components

Cons:

* Additional infrastructure
* More operational complexity

If simplicity became the primary objective, Redis would be removed.

---

## API Layer

### Responsibilities

Expose:

* Metrics
* Funnel
* Heatmap
* Anomalies
* Health status

### Design Goal

Every endpoint should answer a business question.

Examples:

| Endpoint   | Question                           |
| ---------- | ---------------------------------- |
| /metrics   | How is the store performing today? |
| /funnel    | Where are customers dropping off?  |
| /heatmap   | Which zones attract attention?     |
| /anomalies | What requires intervention?        |
| /health    | Is the system operating correctly? |

---

## Metrics Engine

### Responsibility

Convert events into analytics.

### Storage Strategy

Hybrid model:

* Raw events retained
* Session state maintained separately

### Why

Pure event sourcing would be simpler conceptually.

However repeated replay of event history becomes inefficient as traffic grows.

The hybrid approach provides:

* Fast reads
* Simple queries
* Easier debugging

while preserving raw event history.

---

# Data Flow Walkthrough

## Step 1

Visitor enters store.

Detection layer creates a person detection.

Tracking layer assigns a track.

Re-ID determines whether this is:

* New visitor
* Existing visitor
* Returning visitor

ENTRY event emitted.

---

## Step 2

Visitor enters SKINCARE zone.

ZONE_ENTER emitted.

Timer begins.

---

## Step 3

Visitor remains in zone.

ZONE_DWELL emitted every 30 seconds.

---

## Step 4

Visitor enters billing area.

Queue depth calculated.

BILLING_QUEUE_JOIN emitted.

---

## Step 5

POS transaction appears.

Session marked converted.

---

## Step 6

Visitor exits store.

EXIT event emitted.

Session closed.

Metrics updated.

---

# Edge Case Strategy

## Group Entry

### Problem

Multiple visitors enter simultaneously.

### Risk

Under-counting.

### Solution

Combine person detection with head-count validation.

### Remaining Limitation

Dense groups can still be partially merged.

---

## Re-Entry

### Problem

Customer briefly leaves and returns.

### Risk

Inflated visitor counts.

### Solution

Appearance matching against recent visitors.

### Tradeoff

A configurable time window is required.

The chosen value is operational rather than mathematically perfect.

---

## Staff Exclusion

### Problem

Staff should not influence customer metrics.

### Solution

Use:

* Appearance signals
* Behavioural patterns

Both must agree.

### Reasoning

I intentionally avoided relying entirely on uniforms.

The challenge suggests staff uniforms may exist but does not guarantee it.

Behavioural signals provide a second layer of validation.

---

## Partial Occlusion

### Problem

Shelves and displays obscure customers.

### Solution

ByteTrack recovers many low-confidence detections.

Low-confidence events remain visible rather than being silently discarded.

---

## Empty Store Periods

### Problem

No customer traffic.

### Risk

Division-by-zero errors.

### Solution

Metrics return valid zero values.

No special cases required by clients.

---

# Scalability Analysis

Assume:

* 40 stores
* 3 cameras per store
* 15 FPS

Total cameras:

120

Approximate event generation:

Thousands of events per hour.

Primary bottlenecks:

1. Re-ID inference
2. Database writes
3. Materialized view refreshes

Potential future improvements:

* Batch inference
* Horizontal API scaling
* Stream partitioning

---

# Reliability and Observability

## Logging

Every request logs:

* Trace ID
* Endpoint
* Latency
* Store ID

---

## Health Checks

System health includes:

* Database connectivity
* Redis connectivity
* Event freshness

---

## Failure Handling

Database unavailable:

```json
{
  "error": "SERVICE_UNAVAILABLE"
}
```

Returned with HTTP 503.

No internal stack traces exposed.

---

# AI Assisted Decisions

AI was used as a design partner, not as an authority.

---

## Example 1

Question:

Which detector should be used?

AI Recommendation:

RT-DETR

Final Decision:

YOLOv8s

Reason:

Deployment simplicity outweighed small accuracy gains.

---

## Example 2

Question:

Should the system use CQRS?

AI Recommendation:

Yes

Final Decision:

No

Reason:

Additional complexity provided little value within challenge constraints.

---

## Example 3

Question:

How should staff be identified?

AI Recommendation:

Uniform classifier

Final Decision:

Uniform + behaviour signals

Reason:

Uniforms may not always be visible.

Behaviour provides a stronger secondary signal.

---

# Decisions I Reversed

## DeepSORT

Started with DeepSORT.

Observed track fragmentation.

Replaced with ByteTrack.

---

## Immediate Purchase Attribution

Initially considered every billing-zone visitor converted.

Observed false positives.

Switched to POS correlation.

---

## Direct Database Writes

Initially used PostgreSQL directly.

Observed event loss during restart scenarios.

Introduced Redis buffering.

---

# What I Deliberately Did Not Optimize

I could have introduced:

* Kafka
* CQRS
* Distributed tracing
* RT-DETR
* ML forecasting

I intentionally did not.

Once conversion analytics became reliable, additional complexity provided diminishing returns.

The challenge rewards engineering judgement, not architectural maximalism.

---

# Future Improvements

Priority 1

Improve Re-ID accuracy.

---

Priority 2

Introduce historical anomaly baselines.

---

Priority 3

Cross-camera calibration.

---

Priority 4

Store-specific staff classifier training.

---

Priority 5

Load testing with multi-store simulations.

---

# Final Reflection

The hardest problem in this project was not object detection.

It was identity continuity.

Most business metric errors originate from incorrectly linking customer journeys rather than from missed detections.

Given additional time, improving visitor identity quality would produce greater business value than replacing the detector with a more sophisticated model.
