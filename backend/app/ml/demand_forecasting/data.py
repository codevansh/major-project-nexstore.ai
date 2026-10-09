"""Read-only transformation of sales documents into daily product demand."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from numbers import Integral, Real
from typing import Any, Iterable


@dataclass(frozen=True)
class DailyDemand:
    product_id: str
    demand_date: date
    quantity: float


@dataclass(frozen=True)
class DataQualityReport:
    total_transactions: int
    completed_transactions: int
    excluded_non_completed_transactions: int
    invalid_timestamps: int
    eligible_transactions: int
    missing_product_id_lines: int
    invalid_quantity_lines: int
    accepted_sale_lines: int
    observed_through: date | None


@dataclass(frozen=True)
class PreparedSalesData:
    daily_demand: tuple[DailyDemand, ...]
    quality: DataQualityReport


def parse_daily_date(value: Any) -> date | None:
    """Parse BSON datetimes, dates, or ISO strings as UTC calendar dates."""
    try:
        if isinstance(value, datetime):
            parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).date()
        if isinstance(value, date):
            return value
        if isinstance(value, str) and value.strip():
            normalized = value.strip().replace("Z", "+00:00")
            try:
                parsed_dt = datetime.fromisoformat(normalized)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                return parsed_dt.astimezone(timezone.utc).date()
            except ValueError:
                return date.fromisoformat(value.strip())
    except (OverflowError, ValueError, TypeError):
        return None
    return None


def _valid_quantity(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    if not float(value).is_integer():
        return False
    return value > 0


def prepare_sales_data(
    sales_records: Iterable[dict[str, Any]],
    *,
    through_date: date | None = None,
) -> PreparedSalesData:
    """Filter completed sales and aggregate valid items into product/day totals.

    Missing calendar days between each product's first and last observed sale
    are represented as zero demand. When ``through_date`` is provided, records
    after that date are ignored and known product series are extended through
    that date with zero-demand days.
    """
    records = list(sales_records)
    completed = 0
    invalid_timestamps = 0
    eligible = 0
    missing_ids = 0
    invalid_quantities = 0
    accepted_lines = 0
    daily_totals: dict[tuple[str, date], float] = defaultdict(float)
    observed_dates: list[date] = []

    for sale in records:
        if not isinstance(sale, dict) or sale.get("status") != "completed":
            continue
        completed += 1
        sale_date = parse_daily_date(sale.get("created_at"))
        if sale_date is None:
            invalid_timestamps += 1
            continue
        if through_date is not None and sale_date > through_date:
            continue
        eligible += 1
        observed_dates.append(sale_date)
        items = sale.get("items")
        if not isinstance(items, (list, tuple)):
            continue

        for item in items:
            if not isinstance(item, dict):
                missing_ids += 1
                invalid_quantities += 1
                continue
            product_value = item.get("product_id")
            product_id = str(product_value).strip() if product_value is not None else ""
            if not product_id:
                missing_ids += 1
            quantity = item.get("quantity")
            if not _valid_quantity(quantity):
                invalid_quantities += 1
            if not product_id or not _valid_quantity(quantity):
                continue
            daily_totals[(product_id, sale_date)] += float(quantity)
            accepted_lines += 1

    dates_by_product: dict[str, list[date]] = defaultdict(list)
    for product_id, demand_date in daily_totals:
        dates_by_product[product_id].append(demand_date)

    output: list[DailyDemand] = []
    for product_id, dates in sorted(dates_by_product.items()):
        start = min(dates)
        end = through_date if through_date is not None else max(dates)
        current = start
        while current <= end:
            output.append(
                DailyDemand(
                    product_id=product_id,
                    demand_date=current,
                    quantity=daily_totals.get((product_id, current), 0.0),
                )
            )
            current += timedelta(days=1)

    quality = DataQualityReport(
        total_transactions=len(records),
        completed_transactions=completed,
        excluded_non_completed_transactions=len(records) - completed,
        invalid_timestamps=invalid_timestamps,
        eligible_transactions=eligible,
        missing_product_id_lines=missing_ids,
        invalid_quantity_lines=invalid_quantities,
        accepted_sale_lines=accepted_lines,
        observed_through=max(observed_dates) if observed_dates else None,
    )
    return PreparedSalesData(tuple(output), quality)
