from datetime import datetime, timezone


def sale_document(
    invoice_number: str,
    store_id: str,
    customer_id: str | None,
    items: list[dict],
    subtotal: float,
    discount: float,
    total: float,
    payment_method: str,
) -> dict:

    now = datetime.now(timezone.utc)

    return {
        "invoice_number": invoice_number,
        "store_id": store_id,
        "customer_id": customer_id,
        "items": items,
        "totals": {
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
        },
        "payment": {
            "method": payment_method,
            "status": "paid",
        },
        "status": "completed",
        "created_at": now,
        "updated_at": now,
    }
