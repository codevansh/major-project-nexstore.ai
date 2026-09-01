from typing import Any

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    sku: str = Field(
        min_length=1,
        max_length=100,
    )

    barcode: str = Field(
        min_length=4,
        max_length=50,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    category: str = Field(
        min_length=1,
        max_length=100,
    )

    brand: str = Field(
        min_length=1,
        max_length=100,
    )

    cost_price: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    description: str | None = None
    attributes: dict[str, Any] = Field(
        default_factory=dict,
    )


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    brand: str | None = None
    cost_price: float | None = Field(default=None, ge=0)
    selling_price: float | None = Field(default=None, ge=0)
    description: str | None = None
    attributes: dict[str, Any] | None = None
    status: str | None = None


class ProductResponse(BaseModel):
    id: str
    sku: str
    barcode: str
    name: str
    category: str
    brand: str
    cost_price: float
    selling_price: float
    description: str | None
    attributes: dict[str, Any]
    status: str
