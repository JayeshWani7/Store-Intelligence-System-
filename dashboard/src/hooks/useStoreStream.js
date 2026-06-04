/**
 * useStoreStream
 *
 * Connects to GET /stores/{storeId}/stream (SSE) and returns the latest
 * snapshot plus connection state.
 *
 * Returned shape:
 *   { data, status, lastTs, error }
 *
 *   data    – latest parsed SSE payload (null before first message)
 *   status  – "connecting" | "live" | "error" | "idle"
 *   lastTs  – ISO string of last received message timestamp
 *   error   – error message string (null when no error)
 */

import { useEffect, useRef, useState } from "react";

const API_BASE =
  process.env.REACT_APP_API_URL ||
  "http://localhost:8000";

export default function useStoreStream(storeId) {
  const [data, setData]     = useState(null);
  const [status, setStatus] = useState("idle");
  const [lastTs, setLastTs] = useState(null);
  const [error, setError]   = useState(null);
  const esRef               = useRef(null);

  useEffect(() => {
    if (!storeId) {
      setStatus("idle");
      return;
    }

    // Close previous connection if store changes
    if (esRef.current) {
      esRef.current.close();
    }

    setStatus("connecting");
    setData(null);
    setError(null);

    const url = `${API_BASE}/stores/${encodeURIComponent(storeId)}/stream`;
    const es  = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setStatus("live");

    es.onmessage = (evt) => {
      try {
        const parsed = JSON.parse(evt.data);
        if (parsed.error) {
          setError(parsed.error);
          setStatus("error");
        } else {
          setData(parsed);
          setLastTs(parsed.ts ?? new Date().toISOString());
          setStatus("live");
          setError(null);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setStatus("error");
      setError("Stream disconnected — retrying…");
      // EventSource auto-reconnects; we just reflect the state
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [storeId]);

  return { data, status, lastTs, error };
}
