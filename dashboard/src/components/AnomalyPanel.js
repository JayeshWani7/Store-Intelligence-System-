/**
 * AnomalyPanel – list of active anomaly alerts.
 *
 * Props:
 *   anomalies – array from SSE payload.anomalies
 */

import React from "react";

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}

function fmtContext(ctx) {
  if (!ctx || !Object.keys(ctx).length) return null;
  return Object.entries(ctx)
    .map(([k, v]) => `${k}: ${v}`)
    .join("  ·  ");
}

export default function AnomalyPanel({ anomalies }) {
  return (
    <div className="card anomaly-section">
      <div className="card-title">
        Active Anomalies
        {anomalies && anomalies.length > 0 && (
          <span style={{ marginLeft: 8, color: "#ef4444" }}>
            ({anomalies.length})
          </span>
        )}
      </div>

      {!anomalies || anomalies.length === 0 ? (
        <div className="anomaly-empty">✓ No active anomalies</div>
      ) : (
        <div className="anomaly-list">
          {anomalies.map((a, i) => {
            const sev    = (a.severity || "low").toLowerCase();
            const ctxStr = fmtContext(a.context);
            return (
              <div className={`anomaly-item ${sev}`} key={i}>
                <span className={`severity-badge ${sev}`}>{sev}</span>
                <div className="anomaly-body">
                  <div className="anomaly-type">
                    {(a.anomaly_type || "unknown").replace(/_/g, " ")}
                  </div>
                  <div className="anomaly-time">{fmtTime(a.detected_ts)}</div>
                  {ctxStr && <div className="anomaly-context">{ctxStr}</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
