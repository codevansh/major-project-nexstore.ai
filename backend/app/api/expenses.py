from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.database import Database

from app.core.database import get_database
from app.core.security import get_current_user
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def get_expense_service(db: Database = Depends(get_database)) -> ExpenseService:
    return ExpenseService(db)


def serialize_expense(expense: dict) -> dict:
    return {
        "id": str(expense["_id"]),
        "store_id": expense["store_id"],
        "category": expense["category"],
        "amount": expense["amount"],
        "payment_method": expense["payment_method"],
        "description": expense.get("description"),
        "expense_date": expense["expense_date"],
        "status": expense.get("status", "active"),
        "created_at": expense["created_at"],
        "updated_at": expense["updated_at"],
    }


@router.post("", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    expense: ExpenseCreate,
    service: ExpenseService = Depends(get_expense_service),
    _: dict = Depends(get_current_user),
):
    expense_id = service.create_expense(expense)
    created = service.get_expense(expense_id)
    return serialize_expense(created)


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    store_id: str | None = Query(default=None),
    category: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    service: ExpenseService = Depends(get_expense_service),
    _: dict = Depends(get_current_user),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must precede end_date.")

    expenses = service.list_expenses(
        skip=skip,
        limit=limit,
        store_id=store_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    return [serialize_expense(expense) for expense in expenses]


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense(
    expense_id: str,
    service: ExpenseService = Depends(get_expense_service),
    _: dict = Depends(get_current_user),
):
    expense = service.get_expense(expense_id)
    if expense is None or expense.get("status") != "active":
        raise HTTPException(status_code=404, detail="Expense not found.")
    return serialize_expense(expense)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: str,
    expense: ExpenseUpdate,
    service: ExpenseService = Depends(get_expense_service),
    _: dict = Depends(get_current_user),
):
    updated = service.update_expense(expense_id, expense)
    if updated is None or updated.get("status") != "active":
        raise HTTPException(status_code=404, detail="Expense not found.")
    return serialize_expense(updated)


@router.delete("/{expense_id}")
def deactivate_expense(
    expense_id: str,
    service: ExpenseService = Depends(get_expense_service),
    _: dict = Depends(get_current_user),
):
    if not service.deactivate_expense(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found.")
    return {"message": "Expense deactivated successfully.", "expense_id": expense_id}