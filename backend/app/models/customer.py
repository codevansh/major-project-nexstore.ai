from datetime import datetime, timezone


def customer_document(
    name: str,
    email: str | None = None,
    phone: str | None = None,
) -> dict:

    now = datetime.now(timezone.utc)

    return {
        "name": name,
        "contact": {
            "email": email,
            "phone": phone,
        },
        "segment": "new",
        "purchase_summary": {
            "total_orders": 0,
            "total_spent": 0.0,
            "average_order_value": 0.0,
        },
        "created_at": now,
        "updated_at": now,
    }
