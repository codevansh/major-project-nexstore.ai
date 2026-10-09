"""Minimal, privacy-conscious MongoDB extraction for demand training."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any


def load_sales_history(db: Any, *, through_date: date | None = None) -> list[dict]:
    """Read only demand fields from sales; never project customer/payment data."""
    query: dict[str, Any] = {}
    if through_date is not None:
        next_day = datetime.combine(
            through_date + timedelta(days=1), time.min, tzinfo=timezone.utc
        )
        query["created_at"] = {"$lt": next_day}
    projection = {
        "_id": 0,
        "status": 1,
        "created_at": 1,
        "items.product_id": 1,
        "items.quantity": 1,
    }
    return list(db.sales.find(query, projection))
