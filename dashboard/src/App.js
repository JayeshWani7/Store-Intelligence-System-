import React, { useState, useRef } from "react";
import "./App.css";

import useStoreStream          from "./hooks/useStoreStream";
import KpiGrid                 from "./components/KpiGrid";
import FunnelChart             from "./components/FunnelChart";
import HeatmapChart            from "./components/HeatmapChart";
import AnomalyPanel            from "./components/AnomalyPanel";

// ── Default store loaded on start ────────────────────────
const DEFAULT_STORE = "STORE_BLR_002";

function StatusDot({ status }) {
  return <span className={`status-dot ${status === "live" ? "live" : status === "error" ? "error" : ""}`} />;
}

function fmtTs(iso) {
  if (!iso) return null;
  try { return new Date(iso).toLocaleTimeString(); }
  catch { return iso; }
}

export default function App() {
  const [storeId, setStoreId] = useState(DEFAULT_STORE);
  const [inputVal, setInputVal] = useState(DEFAULT_STORE);
  const inputRef = useRef(null);

  const { data, status, lastTs, error } = useStoreStream(storeId);

  const metrics     = data?.metrics     ?? null;
  const funnel      = data?.funnel      ?? null;
  const zoneHeatmap = data?.zone_heatmap ?? null;
  const anomalies   = data?.anomalies   ?? null;

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = inputVal.trim();
    if (trimmed) setStoreId(trimmed);
  }

  return (
    <div className="app">

      {/* ── Header ───────────────────────────────────── */}
      <div className="header">
        <h1>Store <span>Intelligence</span></h1>

        <form className="store-form" onSubmit={handleSubmit}>
          <label htmlFor="store-input">Store ID</label>
          <input
            id="store-input"
            ref={inputRef}
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="e.g. store_001"
            aria-label="Store ID"
          />
          <button type="submit">Connect</button>
        </form>
      </div>

      {/* ── Status bar ───────────────────────────────── */}
      <div className="status-bar" role="status" aria-live="polite">
        <StatusDot status={status} />
        {status === "live"       && <span>Live · {storeId}</span>}
        {status === "connecting" && <span>Connecting to {storeId}…</span>}
        {status === "error"      && <span style={{ color: "#ef4444" }}>{error}</span>}
        {status === "idle"       && <span>Enter a store ID and click Connect</span>}
        {lastTs && status === "live" && (
          <span style={{ marginLeft: "auto" }}>Last update: {fmtTs(lastTs)}</span>
        )}
      </div>

      {/* ── KPI row ──────────────────────────────────── */}
      <KpiGrid metrics={metrics} />

      {/* ── Anomalies ────────────────────────────────── */}
      <AnomalyPanel anomalies={anomalies} />

      {/* ── Funnel + Heatmap ─────────────────────────── */}
      <div className="two-col">
        <FunnelChart  funnel={funnel} />
        <HeatmapChart zoneHeatmap={zoneHeatmap} />
      </div>

      {/* ── Footer ───────────────────────────────────── */}
      <div className="footer">
        Store Intelligence System · streaming from{" "}
        {process.env.REACT_APP_API_URL || "http://localhost:8000"}
      </div>

    </div>
  );
}
