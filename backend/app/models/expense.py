from datetime import datetime, timezone


def expense_document(
    store_id: str,
    category: str,
    amount: float,
    payment_method: str,
    description: str | None,
    expense_date: datetime,
) -> dict:
    now = datetime.now(timezone.utc)

    return {
        "store_id": store_id,
        "category": category,
        "amount": amount,
        "payment_method": payment_method,
        "description": description,
        "expense_date": expense_date,
        "created_at": now,
        "updated_at": now,
        "status": "active",
    }