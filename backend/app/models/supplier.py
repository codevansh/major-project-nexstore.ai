from datetime import datetime, timezone


def supplier_document(
    name: str,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
) -> dict:
    now = datetime.now(timezone.utc)

    return {
        "name": name,
        "contact": {
            "phone": phone,
            "email": email,
        },
        "address": address,
        "status": "active",
        "purchase_summary": {
            "total_purchases": 0,
            "total_purchase_value": 0.0,
        },
        "created_at": now,
        "updated_at": now,
    }