"""Reproducible synthetic sales data for development and pipeline evaluation."""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEED = 42
DEFAULT_DAYS = 120
DEFAULT_PRODUCT_COUNT = 10
DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "dev_data"
    / "synthetic_sales_120_days_seed_42.csv"
)

_WEEKDAY_MULTIPLIERS = (0.82, 0.90, 0.96, 1.00, 1.12, 1.28, 1.14)
CSV_COLUMNS = ("created_at", "status", "product_id", "quantity")


def generate_synthetic_sales(
    *,
    days: int = DEFAULT_DAYS,
    product_count: int = DEFAULT_PRODUCT_COUNT,
    seed: int = DEFAULT_SEED,
    start_date: date = date(2025, 1, 1),
) -> list[dict[str, Any]]:
    """Build deterministic flat rows for the canonical synthetic CSV dataset.

    Demand levels increase by product; each product has a weekly demand pattern,
    a small trend, and seeded day-to-day variation. All identifiers and values
    are synthetic. Rows are adapted to sales documents in memory for training;
    they are never written to MongoDB.
    """
    if days < 1 or product_count < 1:
        raise ValueError("days and product_count must be positive.")

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for product_index in range(product_count):
        product_id = f"synthetic-product-{product_index + 1:02d}"
        base_demand = 5 + product_index * 3

        for day_index in range(days):
            sale_day = start_date + timedelta(days=day_index)
            expected = (
                base_demand
                * _WEEKDAY_MULTIPLIERS[sale_day.weekday()]
                * (1 + 0.0015 * day_index)
            )
            quantity = max(1, round(rng.gauss(expected, max(1.0, expected * 0.12))))
            timestamp = datetime.combine(
                sale_day, time(hour=12), tzinfo=timezone.utc
            ).isoformat()
            rows.append(
                {
                    "created_at": timestamp,
                    "status": "completed",
                    "product_id": product_id,
                    "quantity": quantity,
                }
            )
    return rows


def write_synthetic_sales_csv(
    rows: list[dict[str, Any]],
    path: str | Path = DEFAULT_DATASET_PATH,
) -> Path:
    """Write the synthetic rows as a deterministic CSV file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return destination


def synthetic_rows_to_sales_records(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Adapt flat CSV rows to the minimal sales shape used by preparation."""
    records = []
    for row in rows:
        records.append(
            {
                "created_at": row["created_at"],
                "status": row["status"],
                "items": [
                    {
                        "product_id": row["product_id"],
                        "quantity": int(row["quantity"]),
                    }
                ],
            }
        )
    return records


def load_synthetic_sales_records(
    path: str | Path = DEFAULT_DATASET_PATH,
) -> list[dict[str, Any]]:
    """Read the canonical CSV and adapt it to in-memory sales documents."""
    with Path(path).open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(
                f"Synthetic CSV must have columns: {', '.join(CSV_COLUMNS)}"
            )
        rows = list(reader)
    return synthetic_rows_to_sales_records(rows)
