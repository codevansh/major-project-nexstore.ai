from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)


class PurchaseSummaryResponse(BaseModel):
    total_purchases: int
    total_purchase_value: float


class SupplierResponse(BaseModel):
    id: str
    name: str
    phone: str | None
    email: EmailStr | None
    address: str | None
    status: str
    purchase_summary: PurchaseSummaryResponse
    created_at: datetime
    updated_at: datetime
