# Backend API

This backend serves the pricing workflow described in the project root README.

## What This API Does

1. Reads imported market data from PostgreSQL.
2. Runs the pricing engine to create `price_recommendations`.
3. Serves dashboard and recommendation inbox data.
4. Accepts admin approval, rejection, and custom price actions.

## Active Routers

### Dashboard Router

File:
- `app/routers/dashboard.py`

Responsibilities:
- KPI cards
- executive dashboard opportunities
- AI summary
- recommendation inbox
- inbox approve/reject actions

### Pricing Router

File:
- `app/routers/pricing.py`

Responsibilities:
- import `mobile_data.json` into PostgreSQL
- generate recommendations from imported data
- run full mobile pipeline in one call
- list recommendation rows

### Approvals Router

File:
- `app/routers/approvals.py`

Responsibilities:
- list pending approvals
- approve recommendation
- reject recommendation
- apply custom approved price

## Service Layer

### `app/services/pricing_service.py`

Main responsibilities:

1. Replace market dataset from crawler JSON.
2. Build price comparison candidates from PostgreSQL.
3. Run the pricing engine.
4. Persist recommendation rows.
5. Apply approval decisions and audit logging.

### `app/services/dashboard_service.py`

Main responsibilities:

1. Compute executive dashboard KPIs.
2. Build AI summary and opportunities.
3. Shape recommendation inbox rows for the frontend.

## Engine Flow

The engine is called from `pricing_service.generate_recommendations`.

Execution order:

1. `CompetitorRule`
2. `InventoryRule` fallback
3. `MarginRule`
4. `GuardrailsEngine`

Files:

- `../engine/engine.py`
- `../engine/rules/competitor_rule.py`
- `../engine/rules/inventory_rule.py`
- `../engine/rules/margin_rule.py`
- `../engine/rules/guardrails.py`

## Key Endpoints

### Run Full Mobile Pipeline

```bash
curl -X POST http://localhost:8000/api/v1/pricing/pipeline/mobile \
	-H "Content-Type: application/json" \
	-d '{}'
```

Expected outcome:

1. Market data replaced.
2. Recommendations regenerated.
3. Frontend inbox updates from database state.

### List Pending Approvals

```bash
curl http://localhost:8000/api/v1/approvals/pending
```

### Approve Recommendation

```bash
curl -X POST http://localhost:8000/api/v1/approvals/<recommendation_id>/approve \
	-H "Content-Type: application/json" \
	-d '{"actor":"admin"}'
```

### Custom Price Approval

```bash
curl -X POST http://localhost:8000/api/v1/approvals/<recommendation_id>/custom \
	-H "Content-Type: application/json" \
	-d '{"actor":"admin","customPrice":12990000}'
```

## Backend Use Cases

### Use Case A: Scheduled Background Market Refresh

1. Scheduler calls crawler entrypoint.
2. Crawler writes `mobile_data.json`.
3. Importer loads PostgreSQL.
4. Engine regenerates recommendations.

### Use Case B: Manual Rebuild by API

1. Operator calls `/pricing/pipeline/mobile`.
2. Importer truncates and reloads market tables.
3. Engine generates recommendation rows.
4. Dashboard and inbox read the new state.

### Use Case C: Admin Approval

1. UI calls `/approvals/pending`.
2. User approves or rejects.
3. API updates recommendation status.
4. For approve/custom, `skus.current_price` is updated.
5. Audit tables are written.

## Run

```bash
cd backend/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
