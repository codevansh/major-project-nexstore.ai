# Sales Intelligence Agent

## Workflow and data

`POST /api/agents/sales` uses a LangGraph workflow to identify the requested analysis, retrieve sales metrics through the existing `AnalyticsService`, calculate comparisons and trends, create a measurable explanation, and validate the result with Pydantic.

It analyzes completed documents in the existing `sales` collection. Revenue uses the stored `totals.total`, with line-item and subtotal fallbacks when fields are missing. Units and product-level figures come from the sale's recorded `items`. Product ranking uses the existing `products` collection to include active products with no sales in the low-performing list when the period contains completed orders. No new collection is created.

Without explicit dates, the agent uses the last seven rolling days. Comparison questions compare that range with the preceding seven days. A revenue decline is supported by the actual totals; product insights cite measured unit changes. The response does not claim why sales changed unless recorded data can support the claim. If the prior period has zero revenue, percentage change is `null` because a percentage cannot be calculated from a zero baseline.

The repository has no configured LLM provider or trained sales forecasting model. Numeric metrics and explanations therefore remain deterministic. For a forecast question, the agent reuses the inventory agent's 90-day completed-sales average when at least three distinct sales days exist, labels it `historical_average`, and does not represent it as an ML prediction. Otherwise, the forecast is unavailable and a warning is returned. An injected optional LLM may add nonnumeric lead-in prose; failure falls back to deterministic text.

## Endpoint

`POST /api/agents/sales`

Example period comparison:

```json
{
  "question": "Why did sales decrease compared with last week?",
  "store_id": "store-1",
  "analysis": "comparison"
}
```

Optional fields include `product_id`, `start_date`, `end_date`, `limit`, and `horizon_days`. Provide both start and end dates together. Available analysis values are `summary`, `top_products`, `low_products`, `comparison`, `product_sales`, and `forecast`; if omitted, the agent infers the analysis from the question.

Example requests:

```bash
curl -X POST http://127.0.0.1:8000/api/agents/sales \
  -H 'Content-Type: application/json' \
  -d '{"question":"What were my best-selling products this week?","store_id":"store-1","limit":5}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/agents/sales \
  -H 'Content-Type: application/json' \
  -d '{"question":"Which products are likely to sell more next week?","product_id":"PRODUCT_ID","store_id":"store-1","horizon_days":7}'
```

## Run and test

From the `backend` directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

In another terminal, activate the same environment and run unit and API tests:

```bash
cd major-project-nexstore.ai/backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```
