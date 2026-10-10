from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

from app.services.analytics_service import AnalyticsService
from app.services.inventory_intelligence_service import InventoryIntelligenceTools


class SalesIntelligenceTools:
    """Reusable sales-analysis tools backed by the existing analytics service."""

    def __init__(
        self,
        db: Database,
        *,
        analytics: AnalyticsService | None = None,
        now: datetime | None = None,
    ):
        self.db = db
        self.analytics = analytics or AnalyticsService(db)
        self.forecast_tools = InventoryIntelligenceTools(
            db,
            now=now or datetime.now(timezone.utc),
        )

    def get_sales_summary(
        self,
        start_date: datetime | None,
        end_date: datetime | None,
        store_id: str | None = None,
    ) -> dict:
        return self.analytics.get_sales_summary(start_date, end_date, store_id)

    def get_product_sales(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> dict:
        return self.analytics.get_product_sales(
            product_id,
            start_date,
            end_date,
            store_id,
        )

    def get_top_selling_products(
        self,
        limit: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> list[dict]:
        return self.analytics.get_top_selling_products(
            limit,
            start_date,
            end_date,
            store_id,
        )

    def get_low_performing_products(
        self,
        limit: int,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> list[dict]:
        return self.analytics.get_low_performing_products(
            limit,
            start_date,
            end_date,
            store_id,
        )

    def compare_sales_periods(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        store_id: str | None = None,
    ) -> dict:
        return self.analytics.compare_sales_periods(
            current_start,
            current_end,
            previous_start,
            previous_end,
            store_id,
        )

    def compare_product_sales_periods(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        store_id: str | None = None,
    ) -> list[dict]:
        return self.analytics.compare_product_sales_periods(
            current_start,
            current_end,
            previous_start,
            previous_end,
            store_id,
        )

    def get_demand_forecast(
        self,
        product_id: str,
        horizon: int,
        store_id: str | None = None,
    ) -> dict[str, Any]:
        # No trained ML model is present in this checkout. Reuse the inventory
        # agent's actual-sales historical baseline and preserve its availability
        # signal rather than manufacturing a prediction.
        return self.forecast_tools.get_demand_forecast(
            product_id,
            horizon,
            store_id,
        )
