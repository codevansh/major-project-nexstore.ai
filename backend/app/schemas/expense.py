from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ExpenseCategory = Literal[
    "rent",
    "utilities",
    "salaries",
    "maintenance",
    "marketing",
    "transportation",
    "other",
]


class ExpenseCreate(BaseModel):
    store_id: str = Field(min_length=1, max_length=100)
    category: ExpenseCategory
    amount: float = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    expense_date: datetime


class ExpenseUpdate(BaseModel):
    store_id: str | None = Field(default=None, min_length=1, max_length=100)
    category: ExpenseCategory | None = None
    amount: float | None = Field(default=None, gt=0)
    payment_method: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    expense_date: datetime | None = None


class ExpenseResponse(BaseModel):
    id: str
    store_id: str
    category: str
    amount: float
    payment_method: str
    description: str | None
    expense_date: datetime
    status: str
    created_at: datetime
    updated_at: datetime