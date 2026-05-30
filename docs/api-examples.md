# api-examples.md

# API Examples (Phase 4)

## POST /events/ingest

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_id": "9c9bc6c2-8e6f-4f7e-97c5-99d27d9d2f0d",
        "store_id": "ST1008",
        "visitor_id": "V-0001",
        "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
        "event_type": "ENTRY",
        "event_ts": "2026-04-10T12:15:05Z",
        "camera_id": "cam-entry-1",
        "zone_id": "ENTRY",
        "payload": {"entry_point": "front", "confidence": 0.93},
        "idempotency_key": "cam-entry-1:9c9bc6c2-8e6f-4f7e-97c5-99d27d9d2f0d"
      }
    ]
  }'
```

Sample response:

```json
{
  "accepted": 1,
  "rejected": 0,
  "errors": []
}
```

---

## GET /stores/{id}/metrics

```bash
curl http://localhost:8000/stores/ST1008/metrics
```

Sample response:

```json
{
  "store_id": "ST1008",
  "window_start": null,
  "window_end": null,
  "unique_visitors": 1,
  "converted_visitors": 0,
  "conversion_rate": 0.0,
  "avg_dwell_seconds": 180,
  "avg_queue_seconds": null,
  "abandonment_rate": null,
  "queue_depth": 0,
  "zone_heatmap": {
    "SKINCARE": 30
  }
}
```

---

## GET /stores/{id}/funnel

```bash
curl http://localhost:8000/stores/ST1008/funnel
```

Sample response:

```json
{
  "store_id": "ST1008",
  "entry_count": 1,
  "zone_entry_count": 0,
  "queue_join_count": 0,
  "converted_count": 0,
  "exit_count": 0
}
```

---

## GET /stores/{id}/heatmap

```bash
curl http://localhost:8000/stores/ST1008/heatmap
```

Sample response:

```json
{
  "store_id": "ST1008",
  "zone_heatmap": {
    "SKINCARE": 30
  }
}
```

---

## GET /stores/{id}/anomalies

```bash
curl http://localhost:8000/stores/ST1008/anomalies
```

Sample response:

```json
{
  "store_id": "ST1008",
  "anomalies": []
}
```

---

## GET /health

```bash
curl http://localhost:8000/health
```

Sample response:

```json
{
  "status": "ok",
  "db": "not_configured",
  "redis": "not_configured",
  "event_freshness_seconds": null
}
```
