# LEARNINGS.md

# What I Learned Building This System

This document captures observations, mistakes, tradeoffs, and lessons learned while building the Store Intelligence platform.

The goal is not to document successes.

The goal is to document what changed my understanding of the problem.

---

# Initial Assumption

I initially believed this challenge was primarily a computer vision problem.

After implementation, I no longer think that is true.

Object detection was one of the easier parts of the system.

The harder problems were:

* Identity continuity
* Session construction
* Conversion attribution
* Handling ambiguity

Most business metric errors originated from those areas rather than from missed detections.

---

# Lesson 1 — Detection Accuracy Is Not The Same As Analytics Accuracy

At the beginning I spent significant time comparing detection models.

I quickly realized something important.

A model can have better benchmark accuracy while producing nearly identical business metrics.

For example:

A missed detection inside a product zone may slightly affect dwell calculations.

A missed detection at the store entrance directly impacts conversion rate.

Not all errors have equal business impact.

After realizing this, I changed my evaluation strategy.

I stopped optimizing for model accuracy alone and started optimizing for metric accuracy.

---

# Lesson 2 — Identity Is More Important Than Detection

I expected object detection to be the primary source of error.

It wasn't.

Identity management created significantly larger downstream problems.

Examples:

* Track fragmentation
* Re-entry failures
* Cross-camera mismatches

A single identity error can corrupt:

* Visitor count
* Dwell calculations
* Funnel progression
* Conversion attribution

One identity mistake can affect dozens of downstream events.

One missed detection often affects only a few frames.

This changed where I invested engineering effort.

---

# Lesson 3 — Perfect Accuracy Is Impossible

The challenge provides:

* No customer identifiers
* No identity ground truth
* No explicit re-entry labels

Some decisions are inherently probabilistic.

Examples:

* Re-entry matching
* Staff classification
* Session boundaries

The objective is not eliminating uncertainty.

The objective is exposing uncertainty honestly.

This is why confidence scores remain visible throughout the system.

---

# Lesson 4 — Simplicity Has Value

Several architectures were considered:

* Kafka
* CQRS
* Event Sourcing
* Distributed Processing

All would have made the architecture look more sophisticated.

Very few would have materially improved challenge outcomes.

This reinforced an important lesson:

Engineering quality is not measured by the number of components.

It is measured by how effectively those components solve the problem.

---

# Lesson 5 — Reliability Is A Feature

During development I restarted services repeatedly.

That exposed issues that were invisible during happy-path execution.

Examples:

* Event loss during restarts
* Incomplete sessions
* Delayed processing

Many architectural decisions were influenced by these observations.

Reliability features often appear unnecessary until the first failure occurs.

---

# Lesson 6 — Business Context Matters More Than Technology

Several technical decisions became easier once the business objective was clear.

The North Star metric is:

```text
Conversion Rate
```

Whenever a tradeoff appeared, I asked:

> Does this improve conversion analytics?

This simplified many decisions.

Examples:

* Detector selection
* Tracking strategy
* Session management
* Re-entry handling

The business metric became the decision framework.

---

# Assumptions That Turned Out Wrong

## Wrong Assumption #1

Entering the billing area means a customer intends to purchase.

### Reality

Several visitors entered the billing area and left without completing a transaction.

### Result

Billing-zone presence could not be treated as conversion.

POS correlation became mandatory.

---

## Wrong Assumption #2

Appearance alone would be sufficient for staff identification.

### Reality

Appearance is inconsistent.

Behaviour patterns were often more useful than visual cues.

### Result

Staff classification became a combination of:

* Appearance
* Trajectory
* Zone activity

---

## Wrong Assumption #3

Direct database writes were sufficient.

### Reality

Restart scenarios introduced event loss.

### Result

A buffering mechanism was introduced.

---

# Decisions I Am Most Confident About

## ByteTrack

The switch from DeepSORT was clearly beneficial.

The failure modes became easier to understand and debug.

---

## Denormalized Events

This greatly simplified analytics and troubleshooting.

Every event became independently understandable.

---

## Hybrid Session Storage

Fast queries without losing event history.

This provided a good balance between simplicity and performance.

---

# Decisions I Am Least Confident About

## Re-Entry Threshold

The 30-minute threshold is a judgement call.

Different retailers may require different behaviour.

This should eventually become configurable.

---

## Staff Classification

Without labeled staff examples there is unavoidable uncertainty.

Production deployment would require validation.

---

## POS Correlation Window

The chosen window works reasonably well.

However different store formats may require different timings.

---

# What I Would Do With Another Week

## Priority 1 — Re-ID Evaluation Framework

The largest unknown in the system is identity quality.

I would create:

* Ground truth labels
* Re-entry benchmarks
* Cross-camera evaluation datasets

---

## Priority 2 — Historical Baselines

Current anomaly detection is intentionally simple.

Historical data would enable:

* Better queue predictions
* Better conversion monitoring
* Better anomaly detection

---

## Priority 3 — Cross-Camera Calibration

Camera geometry would improve identity continuity and zone attribution.

---

## Priority 4 — Store-Specific Staff Classification

Generalized staff detection is acceptable.

Store-specific classifiers would be significantly stronger.

---

## Priority 5 — Load Testing

The challenge focuses on correctness.

Given more time I would validate behaviour under sustained multi-store traffic.

---

# What I Would Remove If Simplicity Became The Priority

If forced to reduce complexity:

1. Redis Streams
2. Materialized Views
3. SSE Dashboard Updates

The core analytics platform would still function correctly.

These components primarily improve reliability and user experience.

---

# Biggest Remaining Risk

The biggest remaining risk is identity continuity.

Specifically:

* Re-entry matching
* Cross-camera matching
* Similar-looking customers

If I had to spend one additional engineering day anywhere in the system, it would be here.

Not on detection.

Not on dashboards.

Not on infrastructure.

Identity quality has the largest impact on every downstream business metric.

---

# Final Reflection

Building this system changed how I think about computer vision products.

The difficult part is rarely detecting objects.

The difficult part is converting noisy observations into reliable business decisions.

A useful system is not the one with the most sophisticated model.

It is the one whose outputs stakeholders can trust.

That became the guiding principle behind every major decision in this project.
