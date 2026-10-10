from typing import Literal

from pydantic import BaseModel, Field


class InventoryAgentRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    store_id: str | None = Field(default=None, min_length=1, max_length=100)
    product_id: str | None = Field(default=None, min_length=1, max_length=100)
    horizon_days: int = Field(default=7, ge=1, le=90)


class InventoryRecommendation(BaseModel):
    product_id: str
    product_name: str
    store_id: str
    current_stock: int = Field(ge=0)
    average_daily_demand: float | None = Field(default=None, ge=0)
    predicted_demand: int | None = Field(default=None, ge=0)
    horizon_days: int = Field(ge=1)
    stock_coverage_days: float | None = Field(default=None, ge=0)
    inventory_status: Literal[
        "STOCKOUT", "LOW_STOCK", "AT_RISK", "OVERSTOCK", "HEALTHY"
    ]
    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    recommended_reorder_quantity: int | None = Field(default=None, ge=0)
    forecast_method: Literal["historical_average", "unavailable"]
    reason: str
    requires_human_approval: bool = True


class InventoryAgentResponse(BaseModel):
    agent: Literal["Inventory Intelligence Agent"] = "Inventory Intelligence Agent"
    question: str
    answer: str
    recommendations: list[InventoryRecommendation]
    warnings: list[str] = Field(default_factory=list)
    human_approval_required: bool = True
