from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.models.expense import expense_document
from app.schemas.expense import ExpenseCreate, ExpenseUpdate


class ExpenseService:
    def __init__(self, db: Database):
        self.collection = db.expenses

    def create_expense(self, expense: ExpenseCreate) -> str:
        document = expense_document(
            store_id=expense.store_id,
            category=expense.category,
            amount=expense.amount,
            payment_method=expense.payment_method,
            description=expense.description,
            expense_date=expense.expense_date,
        )
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def get_expense(self, expense_id: str):
        if not ObjectId.is_valid(expense_id):
            return None
        return self.collection.find_one({"_id": ObjectId(expense_id)})

    def list_expenses(
        self,
        skip: int = 0,
        limit: int = 50,
        store_id: str | None = None,
        category: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        query: dict = {"status": "active"}
        if store_id:
            query["store_id"] = store_id
        if category:
            query["category"] = category
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["expense_date"] = date_query

        return list(
            self.collection.find(query)
            .sort("expense_date", -1)
            .skip(skip)
            .limit(limit)
        )

    def update_expense(self, expense_id: str, expense: ExpenseUpdate):
        if not ObjectId.is_valid(expense_id):
            return None

        data = expense.model_dump(exclude_unset=True)
        if not data:
            return self.get_expense(expense_id)

        data["updated_at"] = datetime.now(timezone.utc)
        self.collection.update_one(
            {"_id": ObjectId(expense_id), "status": "active"},
            {"$set": data},
        )
        return self.get_expense(expense_id)

    def deactivate_expense(self, expense_id: str) -> bool:
        if not ObjectId.is_valid(expense_id):
            return False

        result = self.collection.update_one(
            {"_id": ObjectId(expense_id), "status": "active"},
            {
                "$set": {
                    "status": "inactive",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0