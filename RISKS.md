# RISKS.md

# Store Intelligence Risk Register

This document captures the major risks identified during system design and implementation.

The goal is not to eliminate all risks.

The goal is to understand them, monitor them, and reduce their impact on business metrics.

The most important metric affected by these risks is:

**Offline Conversion Rate**

Many risks are acceptable if they do not materially distort conversion analytics.

---

# Detection Risks

## R1 — Missed Person Detections

### Description

A visitor is present in a frame but is not detected.

### Likelihood

Medium

### Impact

Medium

### Business Impact

Missed detections inside product zones primarily affect dwell calculations.

Missed detections near the entry threshold affect visitor counts and conversion rate.

Those are significantly more harmful.

### Mitigation

* Lower confidence recovery through ByteTrack
* Retain low-confidence detections
* Track continuity checks

### Residual Risk

Some occluded visitors will still be missed.

Accepted.

---

## R2 — False Positive Detections

### Description

A non-person object is classified as a person.

Examples:

* Mannequins
* Posters
* Reflections

### Likelihood

Low

### Impact

Low

### Business Impact

Can create artificial visitors.

Usually detectable because the object never moves.

### Mitigation

* Movement validation
* Track duration thresholds
* Static object filtering

### Residual Risk

Very low.

---

## R3 — Group Entry Undercounting

### Description

Multiple visitors enter simultaneously.

Detector merges individuals.

### Likelihood

High

### Impact

Medium

### Business Impact

Undercounting visitors inflates conversion rate.

Example:

Actual:

```text id="oczk4j"
100 visitors
20 purchases
20% conversion
```

Observed:

```text id="l7djfe"
90 visitors
20 purchases
22.2% conversion
```

### Mitigation

* Head-count verification
* Lower NMS threshold
* Entry-zone validation

### Residual Risk

Large groups remain difficult.

---

# Tracking Risks

## R4 — Track Fragmentation

### Description

One visitor receives multiple track IDs.

### Likelihood

Medium

### Impact

High

### Why It Matters

This was one of the most significant issues encountered during development.

Track fragmentation causes:

* Duplicate visitors
* Broken journeys
* Incorrect funnels

### Mitigation

* ByteTrack
* Re-ID verification
* Session repair logic

### Residual Risk

Still present in crowded billing scenarios.

---

## R5 — Track Identity Switching

### Description

Visitor A receives Visitor B's track.

### Likelihood

Low

### Impact

High

### Business Impact

Two customer journeys become merged.

This creates difficult-to-detect analytics corruption.

### Mitigation

* Appearance verification
* Temporal consistency checks
* Active-session validation

### Residual Risk

Low but important.

---

# Re-Identification Risks

## R6 — Failed Re-Entry Recognition

### Description

A returning visitor is treated as a new visitor.

### Likelihood

Medium

### Impact

Medium

### Business Impact

Visitor counts increase.

Conversion rate decreases.

### Example

Single customer:

```text id="g3lg4w"
Visit 1
Leaves
Returns
Purchases
```

Incorrect result:

```text id="0xxdu7"
2 visitors
1 purchase
```

instead of

```text id="2h4x2l"
1 visitor
1 purchase
```

### Mitigation

* Appearance matching
* Session history
* Re-entry windows

### Residual Risk

Re-ID remains the largest source of uncertainty.

---

## R7 — False Re-ID Match

### Description

Two different visitors are merged.

### Likelihood

Low

### Impact

High

### Why This Is Dangerous

This error is harder to detect than a missed re-entry.

Merged visitors can create:

* Impossible journeys
* Incorrect dwell times
* False conversions

### Design Decision

The system intentionally prefers:

```text id="p65sgz"
Split identities
```

over

```text id="m68b0k"
Merged identities
```

because merged identities create more severe downstream damage.

### Residual Risk

Accepted.

---

# Staff Classification Risks

## R8 — Customer Classified As Staff

### Description

A real customer is excluded from analytics.

### Likelihood

Low

### Impact

High

### Business Impact

This removes legitimate customer activity.

The error is invisible.

### Mitigation

Dual validation:

* Appearance
* Behaviour

Both must agree.

### Residual Risk

Low.

---

## R9 — Staff Classified As Customer

### Description

Staff activity appears as customer activity.

### Likelihood

Medium

### Impact

Medium

### Business Impact

Inflates visitor counts.

Creates fake zone interest.

Reduces apparent conversion rate.

### Mitigation

Behaviour-based detection.

### Residual Risk

Acceptable.

---

# POS Correlation Risks

## R10 — Missed Conversion Attribution

### Description

A legitimate purchase is not linked to a visitor.

### Likelihood

Medium

### Impact

High

### Causes

* Clock drift
* Queue delays
* Correlation window too small

### Business Impact

Artificially low conversion rate.

### Mitigation

Configurable windows.

### Residual Risk

Moderate.

---

## R11 — False Conversion Attribution

### Description

Wrong visitor receives purchase credit.

### Likelihood

Low

### Impact

High

### Why It Matters

Conversion rate may remain correct.

Individual journey analytics become incorrect.

This damages funnel accuracy.

### Mitigation

Strict temporal matching.

### Residual Risk

Low.

---

# Infrastructure Risks

## R12 — Database Outage

### Description

PostgreSQL unavailable.

### Likelihood

Low

### Impact

High

### Business Impact

Metrics unavailable.

Event ingestion delayed.

### Mitigation

Redis buffering.

### Graceful Behaviour

Return:

```json id="w2k4ve"
{
  "error": "SERVICE_UNAVAILABLE"
}
```

HTTP 503

### Residual Risk

Low.

---

## R13 — Redis Failure

### Description

Streaming layer unavailable.

### Likelihood

Low

### Impact

Medium

### Mitigation

Fallback to direct database operations.

### Tradeoff

Higher latency.

Lower throughput.

Correctness preserved.

### Residual Risk

Acceptable.

---

## R14 — API Downtime

### Description

API unavailable.

### Likelihood

Low

### Impact

High

### Mitigation

* Health checks
* Container restart policies
* Event buffering

### Residual Risk

Temporary metric unavailability.

---

# Analytics Risks

## R15 — Misleading Heatmaps

### Description

Low traffic periods create misleading visualizations.

### Example

Three visitors:

```text id="3x3t2u"
SKINCARE = 2
MAKEUP = 1
```

Normalization produces:

```text id="udxt8g"
SKINCARE = 100
MAKEUP = 50
```

This appears significant despite tiny sample size.

### Mitigation

Introduce:

```json id="ghxix5"
{
  "data_confidence": false
}
```

when traffic is low.

### Residual Risk

Low.

---

## R16 — Excessive Anomaly Alerts

### Description

Normal variation triggers warnings.

### Likelihood

High

### Impact

Low

### Business Impact

Alert fatigue.

### Mitigation

Require persistence before alerting.

Example:

* Queue spike lasting 10 seconds → ignore
* Queue spike lasting 5 minutes → alert

### Residual Risk

Manageable.

---

# Product Risks

## R17 — Optimizing Technical Metrics Instead Of Business Metrics

### Description

Engineering effort focuses on model accuracy instead of conversion analytics.

### Likelihood

High

### Impact

High

### Why This Risk Exists

Many computer vision projects become benchmark competitions.

The challenge is not asking for the best detector.

It is asking for useful store intelligence.

### Mitigation

Every major decision was evaluated against:

```text id="yozh5q"
Does this improve conversion analytics?
```

### Example

I deliberately rejected:

* Kafka
* CQRS
* RT-DETR
* ML forecasting

because they increased complexity without materially improving the business objective.

### Residual Risk

Low.

---

# Biggest Remaining Risk

If this system were deployed tomorrow, the area I would monitor most closely would be:

**Identity Continuity**

Specifically:

* Re-ID failures
* Re-entry handling
* Cross-camera identity matching

Most business metric errors originate from identity mistakes rather than detection mistakes.

If I had another week of development time, the majority of engineering effort would be invested there.

---

# Final Assessment

The system is designed to fail visibly rather than silently.

When uncertainty exists, it is exposed through:

* Confidence scores
* Health checks
* Data confidence indicators
* Structured anomaly reporting

The objective is not perfect analytics.

The objective is trustworthy analytics.
