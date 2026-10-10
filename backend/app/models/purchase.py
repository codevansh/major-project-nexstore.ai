from datetime import datetime, timezone


def purchase_document(
    invoice_number: str,
    supplier_id: str,
    store_id: str,
    items: list[dict],
    subtotal: float,
    discount: float,
    tax: float,
    total: float,
) -> dict:
    now = datetime.now(timezone.utc)

    return {
        "invoice_number": invoice_number,
        "supplier_id": supplier_id,
        "store_id": store_id,
        "items": items,
        "totals": {
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": total,
        },
        "status": "received",
        "created_at": now,
        "updated_at": now,
    }


PURCHASE_COLLECTION = "purchases"
