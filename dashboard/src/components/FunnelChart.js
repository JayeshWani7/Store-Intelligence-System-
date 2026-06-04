/**
 * FunnelChart – horizontal bar funnel.
 *
 * Props:
 *   funnel – object from SSE payload.funnel
 */

import React from "react";

const STEPS = [
  { key: "entry_count",      label: "Entry" },
  { key: "zone_entry_count", label: "Zone Entry" },
  { key: "queue_join_count", label: "Queue Join" },
  { key: "converted_count",  label: "Converted" },
  { key: "exit_count",       label: "Exit" },
];

export default function FunnelChart({ funnel }) {
  const max = funnel
    ? Math.max(...STEPS.map((s) => funnel[s.key] ?? 0), 1)
    : 1;

  return (
    <div className="card">
      <div className="card-title">Conversion Funnel</div>
      <div className="funnel-list">
        {STEPS.map((step) => {
          const count = funnel ? (funnel[step.key] ?? 0) : 0;
          const pct   = Math.round((count / max) * 100);
          return (
            <div className="funnel-step" key={step.key}>
              <div className="funnel-step-label">{step.label}</div>
              <div className="funnel-bar-wrap">
                <div className="funnel-bar" style={{ width: `${pct}%` }} />
              </div>
              <div className="funnel-step-count">{funnel ? count : "—"}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
