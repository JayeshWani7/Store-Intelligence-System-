/**
 * KpiGrid – row of headline metric cards.
 *
 * Props:
 *   metrics  – object from SSE payload.metrics
 */

import React from "react";

function fmt(val, decimals = 0) {
  if (val === null || val === undefined) return "—";
  return Number(val).toFixed(decimals);
}

function KpiCard({ label, value, unit }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {unit && <div className="kpi-unit">{unit}</div>}
    </div>
  );
}

export default function KpiGrid({ metrics }) {
  if (!metrics) {
    return (
      <div className="kpi-grid">
        {["Visitors", "Converted", "Conversion", "Avg Dwell", "Queue Depth", "Abandonment"].map((l) => (
          <KpiCard key={l} label={l} value="—" />
        ))}
      </div>
    );
  }

  const convPct = fmt(metrics.conversion_rate * 100, 1);
  const abandPct =
    metrics.abandonment_rate !== null && metrics.abandonment_rate !== undefined
      ? fmt(metrics.abandonment_rate * 100, 1)
      : "—";
  const dwell =
    metrics.avg_dwell_seconds !== null && metrics.avg_dwell_seconds !== undefined
      ? fmt(metrics.avg_dwell_seconds, 0)
      : "—";
  const queue =
    metrics.avg_queue_seconds !== null && metrics.avg_queue_seconds !== undefined
      ? fmt(metrics.avg_queue_seconds, 0)
      : "—";

  return (
    <div className="kpi-grid">
      <KpiCard label="Unique Visitors"  value={metrics.unique_visitors}    unit="people" />
      <KpiCard label="Converted"        value={metrics.converted_visitors} unit="people" />
      <KpiCard label="Conversion Rate"  value={`${convPct}%`} />
      <KpiCard label="Avg Dwell"        value={dwell}  unit="sec" />
      <KpiCard label="Avg Queue Wait"   value={queue}  unit="sec" />
      <KpiCard label="Abandonment"      value={abandPct !== "—" ? `${abandPct}%` : "—"} />
      <KpiCard label="Queue Depth"      value={metrics.queue_depth ?? "—"} unit="now" />
    </div>
  );
}
