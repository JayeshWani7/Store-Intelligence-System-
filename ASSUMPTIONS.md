# ASSUMPTIONS.md

# Design Assumptions Register

This document captures assumptions made during implementation.

The challenge intentionally leaves several details undefined.

Rather than hiding assumptions inside code, they are documented explicitly.

Where possible, assumptions are configurable.

Where assumptions materially affect business metrics, the impact is described.

---

# Camera Assumptions

## A1 — Cameras Are Fixed Position

### Assumption

Cameras remain stationary.

No pan, tilt, or zoom occurs during recording.

### Reason

Zone definitions depend on stable camera geometry.

If cameras move, zone polygons become invalid.

### Impact

Zone attribution remains consistent.

### Risk If Wrong

High.

A shifted camera can produce incorrect dwell calculations and heatmaps.

### Mitigation

Future versions should support calibration validation using background reference frames.

---

## A2 — Camera Timestamps Are Reasonably Accurate

### Assumption

Camera clocks do not drift significantly.

### Reason

Visitor activity must be correlated with POS transactions.

### Impact

Enables time-based conversion attribution.

### Risk If Wrong

Medium.

Large clock drift causes missed conversion matches.

### Mitigation

Use configurable matching windows.

Log suspicious timestamp discrepancies.

---

## A3 — Entry Camera Fully Covers Entry Threshold

### Assumption

All visitors pass through the monitored threshold.

### Reason

Visitor counting depends on observing every entry.

### Impact

Accurate denominator for conversion rate.

### Risk If Wrong

High.

Missed entries artificially increase conversion rate.

### Why This Matters

A missed customer who purchases still appears in POS data.

The conversion numerator increases while the denominator does not.

This creates a misleadingly strong conversion rate.

---

# Visitor Assumptions

## V1 — Re-Entry Within 30 Minutes Belongs To Same Session

### Assumption

Visitors returning within 30 minutes are treated as the same session.

### Reason

The challenge provides no ground-truth definition for re-entry.

This value was selected as a practical operational threshold.

### Tradeoff

Short threshold:

* Overcounts visitors

Long threshold:

* Merges independent visits

### Why I Chose This

The cost of inflating visitor counts is greater than occasionally merging visits.

Inflated visitor counts directly distort conversion rate.

Merged visits primarily affect session segmentation.

### Risk If Wrong

Medium.

---

## V2 — Temporary Disappearance Does Not Immediately Mean Exit

### Assumption

A customer may disappear briefly because of:

* Occlusion
* Camera blind spots
* Tracking failure

### Reason

Retail environments are visually noisy.

### Impact

Prevents premature EXIT events.

### Risk If Wrong

Low.

Delayed exits are less harmful than duplicate sessions.

---

## V3 — Visitor Identity Is Probabilistic

### Assumption

Identity matching is not perfect.

### Reason

No customer identifier exists.

Re-ID relies on appearance similarity.

### Impact

Some identity mistakes are unavoidable.

### Design Choice

The system prefers avoiding false merges.

Two customers incorrectly merged into one visitor create more severe downstream analytics errors than splitting one customer into two sessions.

---

# Staff Classification Assumptions

## S1 — Staff Are Visually Or Behaviourally Distinguishable

### Assumption

Staff can be identified through:

* Appearance
* Movement patterns
* Zone traversal behaviour

### Reason

The challenge references staff movement but does not guarantee uniform visibility.

### Why Behaviour Matters

Appearance alone is unreliable.

A customer may resemble staff.

A staff member may not always wear clearly visible branding.

Behaviour provides a second signal.

### Impact

Improves exclusion accuracy.

### Risk If Wrong

Medium.

---

## S2 — Staff Behaviour Differs From Customer Behaviour

### Assumption

Staff typically visit more zones than customers.

### Reason

Staff duties require movement across the store.

Customers usually focus on fewer areas.

### Impact

Supports trajectory-based classification.

### Risk If Wrong

Low.

---

# POS Assumptions

## P1 — Transactions Represent Genuine Purchases

### Assumption

POS records correspond to completed purchases.

### Reason

The challenge dataset primarily contains sales records.

### Impact

Enables conversion attribution.

### Risk If Wrong

Medium.

Returns and corrections would require separate handling.

---

## P1a — POS Dataset Contains Sales Only

### Assumption

The provided POS file contains only completed sales invoices.

### Evidence

The April 10 dataset shows `invoice_type = sales` for every row and no populated `return_id`.

### Impact

Conversion attribution can ignore return flows without distorting the numerator.

### Risk If Wrong

Medium.

Undetected returns would inflate conversion and revenue metrics.

---

## P1b — POS Data Is Store-Scoped

### Assumption

All POS records in a file belong to a single store.

### Evidence

The sample file contains only `store_id = ST1008` and `store_name = Brigade_Bangalore`.

### Impact

Store-level metrics can be computed without cross-store disambiguation.

### Risk If Wrong

Low.

Mixed-store files would require additional partitioning rules.

---

## P1c — POS Timestamps Are Reliable Within A Day

### Assumption

POS timestamps for a given day are internally consistent and usable for matching windows.

### Evidence

The sample file shows a single-day time range without gaps across the operating window.

### Impact

Time-based matching remains the primary conversion attribution method.

### Risk If Wrong

Medium.

Clock drift or time zone errors could cause missed matches.

---

## P2 — Time Correlation Is The Only Reliable Matching Signal

### Assumption

Visitors are linked to purchases through time windows.

### Reason

The challenge explicitly avoids customer identity linkage.

### Why I Did Not Use Customer Identity

Even if customer identifiers existed:

* Privacy concerns increase
* Additional compliance requirements appear
* The challenge objective is behavioural analytics

Time correlation is the simplest privacy-preserving approach.

### Risk If Wrong

Low.

---

## P3 — Billing Zone Indicates Purchase Intent

### Assumption

Visitors entering the billing area are demonstrating purchase intent.

### Reason

Billing zones are designed for checkout.

### Important Limitation

Purchase intent is not purchase completion.

Several visitors may:

* Enter the queue
* Wait briefly
* Leave without purchasing

### Design Consequence

Conversion is only assigned after POS confirmation.

Not after billing zone entry.

---

# Zone Assumptions

## Z1 — A Visitor Belongs To One Zone At A Time

### Assumption

A visitor can only occupy one business zone simultaneously.

### Reason

Analytics require unambiguous attribution.

### Tradeoff

Real-world boundaries are fuzzy.

Zone boundaries are not.

### Resolution Strategy

When a visitor is near a boundary:

* Choose the closest zone centroid
* Prefer continuity with previous zone

### Risk If Wrong

Low.

---

## Z2 — Zone Definitions Are Correct

### Assumption

Store layout polygons accurately represent business zones.

### Reason

The analytics pipeline depends entirely on these definitions.

### Impact

Affects:

* Heatmaps
* Dwell calculations
* Funnel analysis

### Risk If Wrong

High.

Incorrect zone geometry propagates through every downstream metric.

---

# Analytics Assumptions

## AN1 — Conversion Rate Is The Primary Business Metric

### Assumption

Offline conversion rate is the most important KPI.

### Reason

The challenge repeatedly references conversion as the North Star metric.

### Design Impact

When tradeoffs occurred:

Priority order was:

1. Visitor count accuracy
2. Conversion accuracy
3. Dwell accuracy
4. Heatmap precision

### Why

A perfect heatmap with incorrect conversion numbers has limited business value.

The reverse is far more useful.

---

## AN2 — Explainability Is More Valuable Than Maximum Accuracy

### Assumption

A system that can explain its mistakes is preferable to one that produces opaque outputs.

### Reason

Retail operations teams need trust.

Not just predictions.

### Design Consequence

The system logs:

* Confidence scores
* Identity uncertainty
* Data quality indicators

instead of hiding uncertainty.

### Risk If Wrong

Low.

The operational benefits outweigh the additional complexity.

---

# Final Reflection

Every assumption in this document exists because the challenge intentionally leaves some aspects undefined.

The objective was not eliminating assumptions.

The objective was making them explicit, measurable, and easy to revisit as more information becomes available.
