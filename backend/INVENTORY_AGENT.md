# Inventory Intelligence Agent

## Workflow

`POST /api/agents/inventory` runs a LangGraph workflow with four steps:

1. **Retrieve:** Read inventory from the existing `inventory` collection, product details from `products`, and completed sale line items from `sales`.
2. **Evaluate:** Calculate a 90-day historical average, horizon demand, and stock coverage from recorded quantities. A forecast is unavailable until sales occurred on at least three distinct dates.
3. **Recommend:** Flag stockouts, low stock, short coverage, and overstock. The overstock review threshold is 60 days of calculated coverage. Reorder quantities use horizon demand, optional recorded lead-time and safety-stock fields, and the inventory record's configured reorder quantity when its existing reorder threshold is breached.
4. **Validate:** Validate the result with Pydantic before returning JSON.

The repository did not contain a trained forecasting model or LLM provider configuration. The agent therefore uses a deterministic historical-average forecast and factual response text. It never fabricates demand when history is insufficient. An optional injected LLM can add a brief lead-in; failures are ignored and its prose cannot change structured values or reasons. No new collection is created, and the workflow does not write stock, purchases, or purchase orders. Any reorder suggestion requires human approval.

## API

`POST /api/agents/inventory`

```json
{
  "question": "Which products should I reorder this week?",
  "store_id": "store-1",
  "horizon_days": 7
}
```

`store_id` and `product_id` are optional. Omitting `store_id` evaluates all stores separately. The response includes each flagged product's current stock, forecast when available, coverage, status, risk, reorder quantity, factual reason, warnings, and a human-approval flag. Missing product details and malformed stock records are reported in `warnings` or skipped.

Example request from the backend directory:

```bash
curl -X POST http://127.0.0.1:8000/api/agents/inventory \
  -H 'Content-Type: application/json' \
  -d '{"question":"Which products should I reorder this week?","store_id":"store-1","horizon_days":7}'
```

## Install, run, and test

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

In a second terminal, from `backend`, activate the same environment and run:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```
