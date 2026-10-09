# Development data

Files in this directory are synthetic fixtures for local development and
pipeline checks. They are not exports from MongoDB and do not represent real
customers, stores, products, or sales.

The canonical forecasting dataset is `synthetic_sales_120_days_seed_42.csv`.
It has 1,200 rows with these columns:

| Column | Meaning |
|---|---|
| `created_at` | Synthetic UTC sale timestamp in ISO 8601 format |
| `status` | Sale status (`completed`) |
| `product_id` | Synthetic product identifier |
| `quantity` | Positive integer units sold |

The generator uses seed 42, ten products, and 120 days with distinct demand
levels, weekday patterns, a small trend, and random variation. Re-running it
reproduces the same CSV. During training, the CSV rows are adapted in memory
into the minimal sales structure expected by the existing forecasting pipeline;
they are never inserted into MongoDB.

Run isolated training and evaluation from `backend/` with:

```powershell
python -m app.ml.demand_forecasting.train_synthetic
```

The command reads the existing CSV without rewriting it and writes its model
artifact separately under `app/ml/artifacts/`. If the CSV is absent, the command
creates the deterministic seed-42 dataset first. To explicitly regenerate it,
run `python -m app.ml.demand_forecasting.train_synthetic --regenerate`.
Synthetic evaluation is only a pipeline check and does not estimate real-world
forecasting accuracy.
