from datetime import datetime, timezone


def supplier_document(
    name: str,
<<<<<<< HEAD
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
=======
    phone: str | None,
    email: str | None,
    address: str | None,
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
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