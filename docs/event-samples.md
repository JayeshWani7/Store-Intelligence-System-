# event-samples.md

# Event Samples (Phase 3)

## Common Fields

- event_id: UUID
- store_id: string
- visitor_id: string
- session_id: string
- event_type: string
- event_ts: ISO 8601 timestamp
- camera_id: optional
- zone_id: optional
- payload: object
- idempotency_key: string

---

## ENTRY

```json
{
  "event_id": "9c9bc6c2-8e6f-4f7e-97c5-99d27d9d2f0d",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "ENTRY",
  "event_ts": "2026-04-10T12:15:05Z",
  "camera_id": "cam-entry-1",
  "zone_id": "ENTRY",
  "payload": {
    "entry_point": "front",
    "confidence": 0.93
  },
  "idempotency_key": "cam-entry-1:9c9bc6c2-8e6f-4f7e-97c5-99d27d9d2f0d"
}
```

## EXIT

```json
{
  "event_id": "0b67f927-5f86-4c38-9b5e-4c96371a2e52",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "EXIT",
  "event_ts": "2026-04-10T12:57:11Z",
  "camera_id": "cam-entry-1",
  "zone_id": "EXIT",
  "payload": {
    "exit_point": "front",
    "confidence": 0.91
  },
  "idempotency_key": "cam-entry-1:0b67f927-5f86-4c38-9b5e-4c96371a2e52"
}
```

## ZONE_ENTER

```json
{
  "event_id": "8efad1b6-2c5d-4f10-9f79-4a3d6f0f3e2c",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "ZONE_ENTER",
  "event_ts": "2026-04-10T12:20:10Z",
  "camera_id": "cam-aisle-1",
  "zone_id": "SKINCARE",
  "payload": {
    "zone_name": "SKINCARE"
  },
  "idempotency_key": "cam-aisle-1:8efad1b6-2c5d-4f10-9f79-4a3d6f0f3e2c"
}
```

## ZONE_EXIT

```json
{
  "event_id": "ac6e1f2a-6c61-4674-82f0-2992e7aa66f1",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "ZONE_EXIT",
  "event_ts": "2026-04-10T12:30:00Z",
  "camera_id": "cam-aisle-1",
  "zone_id": "SKINCARE",
  "payload": {
    "zone_name": "SKINCARE"
  },
  "idempotency_key": "cam-aisle-1:ac6e1f2a-6c61-4674-82f0-2992e7aa66f1"
}
```

## ZONE_DWELL

```json
{
  "event_id": "f5c1b2f8-4b4e-4f74-8b21-0d73b6bb02d1",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "ZONE_DWELL",
  "event_ts": "2026-04-10T12:21:00Z",
  "camera_id": "cam-aisle-1",
  "zone_id": "SKINCARE",
  "payload": {
    "zone_name": "SKINCARE",
    "dwell_seconds": 30
  },
  "idempotency_key": "cam-aisle-1:f5c1b2f8-4b4e-4f74-8b21-0d73b6bb02d1"
}
```

## BILLING_QUEUE_JOIN

```json
{
  "event_id": "eb9a5a8c-6a1d-42a8-86b1-7d4bb556c0e2",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "BILLING_QUEUE_JOIN",
  "event_ts": "2026-04-10T12:40:00Z",
  "camera_id": "cam-billing-1",
  "zone_id": "BILLING",
  "payload": {
    "queue_depth": 3
  },
  "idempotency_key": "cam-billing-1:eb9a5a8c-6a1d-42a8-86b1-7d4bb556c0e2"
}
```

## BILLING_QUEUE_ABANDON

```json
{
  "event_id": "df703f6a-6f84-4c5a-b9a9-232f6e2f1b69",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "BILLING_QUEUE_ABANDON",
  "event_ts": "2026-04-10T12:44:30Z",
  "camera_id": "cam-billing-1",
  "zone_id": "BILLING",
  "payload": {
    "queue_depth": 2,
    "wait_seconds": 270
  },
  "idempotency_key": "cam-billing-1:df703f6a-6f84-4c5a-b9a9-232f6e2f1b69"
}
```

## REENTRY

```json
{
  "event_id": "44b5d34a-71a1-47f2-a4b1-f5c1c5df9d1b",
  "store_id": "ST1008",
  "visitor_id": "V-0001",
  "session_id": "ST1008-V-0001-2026-04-10T12:15:05Z",
  "event_type": "REENTRY",
  "event_ts": "2026-04-10T13:10:00Z",
  "camera_id": "cam-entry-1",
  "zone_id": "ENTRY",
  "payload": {
    "gap_seconds": 420,
    "match_confidence": 0.86
  },
  "idempotency_key": "cam-entry-1:44b5d34a-71a1-47f2-a4b1-f5c1c5df9d1b"
}
```
