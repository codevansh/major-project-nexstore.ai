import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


HISTORY_LOOKBACK_DAYS = 90
MINIMUM_SALES_DAYS = 3
OVERSTOCK_COVERAGE_DAYS = 60


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _nonnegative_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number >= 0 else None


class InventoryIntelligenceTools:
    """Read-only inventory tools over the project's existing MongoDB collections."""

    def __init__(
        self,
        db: Database,
        *,
        now: datetime | None = None,
    ):
        self.db = db
        self._now = now or datetime.now(timezone.utc)

    def get_inventory(self, store_id: str | None = None) -> list[dict]:
        query = {"store_id": store_id} if store_id else {}
        return list(self.db.inventory.find(query))

    def get_product_details(self, product_id: str) -> dict | None:
        if ObjectId.is_valid(product_id):
            return self.db.products.find_one({"_id": ObjectId(product_id)})
        return self.db.products.find_one({"sku": product_id})

    def get_sales_history(
        self,
        product_id: str,
        store_id: str | None = None,
        lookback_days: int = HISTORY_LOOKBACK_DAYS,
    ) -> list[dict[str, Any]]:
        cutoff = self._now - timedelta(days=lookback_days)
        query: dict[str, Any] = {
            "status": "completed",
            "items.product_id": product_id,
        }
        if store_id:
            query["store_id"] = store_id

        quantities_by_day: dict[str, int] = defaultdict(int)
        sales = self.db.sales.find(
            query,
            {"items": 1, "created_at": 1, "sale_date": 1},
        )
        for sale in sales:
            sold_at = _as_datetime(sale.get("sale_date") or sale.get("created_at"))
            if sold_at is None or sold_at < cutoff or sold_at > self._now:
                continue
            for item in sale.get("items", []):
                if str(item.get("product_id")) != product_id:
                    continue
                quantity = _nonnegative_int(item.get("quantity"))
                if quantity:
                    quantities_by_day[sold_at.date().isoformat()] += quantity

        return [
            {"date": day, "quantity": quantity}
            for day, quantity in sorted(quantities_by_day.items())
        ]

    def get_demand_forecast(
        self,
        product_id: str,
        horizon: int,
        store_id: str | None = None,
        *,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        daily_history = history
        if daily_history is None:
            daily_history = self.get_sales_history(product_id, store_id)

        sales_days = len(daily_history)
        total_units = sum(
            _nonnegative_int(day.get("quantity")) or 0 for day in daily_history
        )
        if sales_days < MINIMUM_SALES_DAYS or total_units <= 0:
            return {
                "product_id": product_id,
                "horizon_days": horizon,
                "predicted_units": None,
                "average_daily_demand": None,
                "history_days": sales_days,
                "history_units": total_units,
                "method": "unavailable",
            }

        # Divide by the complete observation window so no-sale days are not
        # silently discarded from the average.
        average_daily_demand = total_units / HISTORY_LOOKBACK_DAYS
        return {
            "product_id": product_id,
            "horizon_days": horizon,
            "predicted_units": math.ceil(average_daily_demand * horizon),
            "average_daily_demand": round(average_daily_demand, 4),
            "history_days": sales_days,
            "history_units": total_units,
            "method": "historical_average",
        }

    def _inventory_for_product(
        self,
        product_id: str,
        store_id: str | None = None,
    ) -> list[dict]:
        query: dict[str, Any] = {"product_id": product_id}
        if store_id:
            query["store_id"] = store_id
        return list(self.db.inventory.find(query))

    def calculate_stock_coverage(
        self,
        product_id: str,
        store_id: str | None = None,
        *,
        forecast: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inventory_records = self._inventory_for_product(product_id, store_id)
        if not inventory_records:
            return {
                "product_id": product_id,
                "available_stock": None,
                "average_daily_demand": None,
                "coverage_days": None,
            }

        available = 0
        for record in inventory_records:
            stock = record.get("stock", {})
            quantity = _nonnegative_int(stock.get("available"))
            if quantity is None:
                return {
                    "product_id": product_id,
                    "available_stock": None,
                    "average_daily_demand": None,
                    "coverage_days": None,
                }
            available += quantity

        if forecast is None:
            forecast = self.get_demand_forecast(product_id, 7, store_id)
        average = forecast.get("average_daily_demand")
        coverage = available / average if average and average > 0 else None
        return {
            "product_id": product_id,
            "available_stock": available,
            "average_daily_demand": average,
            "coverage_days": round(coverage, 2) if coverage is not None else None,
        }

    def calculate_reorder_quantity(
        self,
        product_id: str,
        horizon: int,
        store_id: str | None = None,
        *,
        forecast: dict[str, Any] | None = None,
        inventory_record: dict[str, Any] | None = None,
        product_details: dict[str, Any] | None = None,
    ) -> int | None:
        if inventory_record is None:
            records = self._inventory_for_product(product_id, store_id)
            if not records:
                return None
            if len(records) > 1 and store_id is None:
                return None
            inventory_record = records[0]

        stock = inventory_record.get("stock", {})
        available = _nonnegative_int(stock.get("available"))
        if available is None:
            return None

        thresholds = inventory_record.get("thresholds", {})
        reorder = inventory_record.get("reorder", {})
        reorder_level = _nonnegative_int(thresholds.get("reorder_level"))
        configured_quantity = _nonnegative_int(reorder.get("recommended_quantity"))

        if forecast is None:
            forecast = self.get_demand_forecast(product_id, horizon, store_id)
        predicted_demand = forecast.get("predicted_units")
        if predicted_demand is None:
            if available == 0 or (
                reorder_level is not None and available <= reorder_level
            ):
                return configured_quantity
            return None

        target_period = horizon
        supply = (product_details or {}).get("supply", {})
        lead_time_value = reorder.get("lead_time_days")
        if lead_time_value is None:
            lead_time_value = inventory_record.get("lead_time_days")
        if lead_time_value is None:
            lead_time_value = supply.get("lead_time_days")
        if lead_time_value is None:
            lead_time_value = (product_details or {}).get("lead_time_days")
        lead_time = _nonnegative_int(lead_time_value)
        if lead_time:
            target_period = lead_time
        average = forecast.get("average_daily_demand") or 0
        target_stock = math.ceil(average * target_period)

        safety_stock_value = reorder.get("safety_stock")
        if safety_stock_value is None:
            safety_stock_value = inventory_record.get("safety_stock")
        if safety_stock_value is None:
            safety_stock_value = supply.get("safety_stock")
        if safety_stock_value is None:
            safety_stock_value = (product_details or {}).get("safety_stock")
        safety_stock = _nonnegative_int(safety_stock_value)
        if safety_stock is not None:
            target_stock += safety_stock

        quantity_needed = max(0, target_stock - available)
        if (
            reorder_level is not None
            and available <= reorder_level
            and configured_quantity is not None
        ):
            quantity_needed = max(quantity_needed, configured_quantity)
        return quantity_needed
