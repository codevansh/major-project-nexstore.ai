from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SalesAgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    store_id: str | None = Field(default=None, min_length=1, max_length=100)
    product_id: str | None = Field(default=None, min_length=1, max_length=100)
    analysis: Literal[
        "summary",
        "top_products",
        "low_products",
        "comparison",
        "product_sales",
        "forecast",
    ] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(default=10, ge=1, le=100)
    horizon_days: int = Field(default=7, ge=1, le=90)

    @model_validator(mode="after")
    def validate_date_range(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("start_date and end_date must be provided together.")
        if self.start_date and self.end_date:
            start = self.start_date
            end = self.end_date
            start = (
                start.replace(tzinfo=timezone.utc)
                if start.tzinfo is None
                else start.astimezone(timezone.utc)
            )
            end = (
                end.replace(tzinfo=timezone.utc)
                if end.tzinfo is None
                else end.astimezone(timezone.utc)
            )
            if start > end:
                raise ValueError("start_date must be earlier than or equal to end_date.")
            self.start_date = start
            self.end_date = end
        return self


class SalesPeriodMetrics(BaseModel):
    revenue: float = Field(ge=0)
    units_sold: int = Field(ge=0)
    order_count: int = Field(ge=0)
    average_order_value: float = Field(ge=0)


class SalesAgentMetrics(BaseModel):
    current_period_revenue: float = Field(ge=0)
    current_period_units_sold: int = Field(ge=0)
    current_period_order_count: int = Field(ge=0)
    current_period_average_order_value: float = Field(ge=0)
    previous_period_revenue: float | None = Field(default=None, ge=0)
    previous_period_units_sold: int | None = Field(default=None, ge=0)
    previous_period_order_count: int | None = Field(default=None, ge=0)
    previous_period_average_order_value: float | None = Field(default=None, ge=0)
    revenue_change: float | None = None
    revenue_change_percent: float | None = None
    units_change: int | None = None
    units_change_percent: float | None = None


class ProductSalesMetric(BaseModel):
    product_id: str
    product_name: str
    barcode: str | None = None
    units_sold: int = Field(ge=0)
    revenue: float = Field(ge=0)
    order_count: int = Field(ge=0)


class SalesInsight(BaseModel):
    product_id: str
    product_name: str
    trend: Literal["INCREASING", "DECLINING", "STABLE"]
    current_units_sold: int = Field(ge=0)
    previous_units_sold: int = Field(ge=0)
    current_revenue: float = Field(ge=0)
    previous_revenue: float = Field(ge=0)
    units_change_percent: float | None = None
    reason: str


class DemandForecastResult(BaseModel):
    product_id: str
    product_name: str
    horizon_days: int = Field(ge=1)
    predicted_units: int | None = Field(default=None, ge=0)
    average_daily_demand: float | None = Field(default=None, ge=0)
    method: Literal["historical_average", "unavailable"]
    reason: str


class SalesAgentResponse(BaseModel):
    agent: Literal["Sales Intelligence Agent"] = "Sales Intelligence Agent"
    summary: str
    metrics: SalesAgentMetrics
    product_sales: ProductSalesMetric | None = None
    top_selling_products: list[ProductSalesMetric] = Field(default_factory=list)
    low_performing_products: list[ProductSalesMetric] = Field(default_factory=list)
    insights: list[SalesInsight] = Field(default_factory=list)
    forecasts: list[DemandForecastResult] = Field(default_factory=list)
    data_period: str
    warnings: list[str] = Field(default_factory=list)
