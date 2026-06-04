/**
 * HeatmapChart – horizontal bar heatmap for zone dwell counts.
 *
 * Props:
 *   zoneHeatmap – Record<string, number> from SSE payload.zone_heatmap
 */

import React from "react";

// Interpolate between cool blue → warm red based on intensity 0–1
function heatColor(intensity) {
  // Blue (60, 130, 246) → Orange (249, 115, 22) → Red (239, 68, 68)
  const stops = [
    { t: 0.0,  r: 60,  g: 130, b: 246 },
    { t: 0.5,  r: 249, g: 115, b: 22  },
    { t: 1.0,  r: 239, g: 68,  b: 68  },
  ];

  let lo = stops[0], hi = stops[1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (intensity <= stops[i + 1].t) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
    lo = stops[i + 1];
    hi = stops[i + 1];
  }

  const span = hi.t - lo.t || 1;
  const f    = (intensity - lo.t) / span;
  const r    = Math.round(lo.r + f * (hi.r - lo.r));
  const g    = Math.round(lo.g + f * (hi.g - lo.g));
  const b    = Math.round(lo.b + f * (hi.b - lo.b));
  return `rgb(${r},${g},${b})`;
}

export default function HeatmapChart({ zoneHeatmap }) {
  const entries = zoneHeatmap
    ? Object.entries(zoneHeatmap).sort((a, b) => b[1] - a[1])
    : [];

  const max = entries.length ? entries[0][1] : 1;

  if (!entries.length) {
    return (
      <div className="card">
        <div className="card-title">Zone Heatmap</div>
        <div className="anomaly-empty">No zone data yet</div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Zone Heatmap</div>
      <div className="heatmap-list">
        {entries.map(([zone, count]) => {
          const intensity = max > 0 ? count / max : 0;
          const pct       = Math.round(intensity * 100);
          return (
            <div className="heatmap-row" key={zone}>
              <div className="heatmap-zone-label" title={zone}>{zone}</div>
              <div className="heatmap-bar-wrap">
                <div
                  className="heatmap-bar"
                  style={{
                    width: `${pct}%`,
                    background: heatColor(intensity),
                    opacity: 0.85 + 0.15 * intensity,
                  }}
                />
              </div>
              <div className="heatmap-count">{count}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
