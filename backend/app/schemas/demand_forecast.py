from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class DemandForecastPointResponse(BaseModel):
    date: date
    predicted_quantity: float = Field(ge=0, allow_inf_nan=False)


class DemandForecastResponse(BaseModel):
    is_synthetic_demo: Literal[True]
    demo_label: Literal["Synthetic demo forecast"]
    data_source: Literal["synthetic development CSV"]
    data_as_of: date
    product_id: str
    forecast_origin: date
    horizon_days: int = Field(ge=1, le=30)
    unit: str
    model: str
    forecasts: list[DemandForecastPointResponse]
