<<<<<<< HEAD
from pydantic import BaseModel, Field
=======
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
<<<<<<< HEAD
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    address: str | None = None
=======
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
<<<<<<< HEAD
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    address: str | None = None
    status: str | None = None
=======
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=300)


class PurchaseSummaryResponse(BaseModel):
    total_purchases: int
    total_purchase_value: float
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)


class SupplierResponse(BaseModel):
    id: str
    name: str
    phone: str | None
<<<<<<< HEAD
    email: str | None
    address: str | None
    status: str
    total_purchases: int
    total_purchase_value: float
=======
    email: EmailStr | None
    address: str | None
    status: str
    purchase_summary: PurchaseSummaryResponse
    created_at: datetime
    updated_at: datetime
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
