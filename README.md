# Store Intelligence System

Store Intelligence System is a FastAPI backend for reconstructing in-store journeys from CCTV-derived events and POS data. It focuses on conversion analytics, dwell time, funnels, and anomaly detection for physical retail.

## Highlights

- Event ingestion API with idempotency support
- Metrics endpoints for conversion rate, visitors, and heatmaps
- Funnel and anomaly endpoints for behavior analysis
- Clean separation of API, services, repositories, and pipeline schemas

## Repository Map

- app/ - FastAPI app and business logic
- pipeline/ - event schemas and pipeline building blocks
- tests/ - API tests and sample flows
- docs/ - architecture, schema, and implementation notes

## Quickstart

1. Create a virtual environment and install dependencies (not pinned in this repo).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn pydantic pytest
```

2. Run the API server.

```bash
uvicorn app.main:app --reload
```

3. Verify health.

```bash
curl http://127.0.0.1:8000/health
```

## Key Endpoints

- `POST /events/ingest` - ingest event batches
- `GET /stores/{store_id}/metrics` - store metrics
- `GET /stores/{store_id}/funnel` - funnel analytics
- `GET /stores/{store_id}/heatmap` - zone dwell heatmap
- `GET /stores/{store_id}/anomalies` - anomaly detection
- `GET /health` - service status

## Tests

```bash
pytest -q
```

## Docs

See docs/ for architecture, schema, and implementation plans.
