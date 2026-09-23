<<<<<<< HEAD
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
=======
"""MongoDB purchase document field conventions.

Purchase documents are created by the existing purchase workflow outside this
checkout. This module documents the persisted shape without adding creation
logic to the restored read API.
"""

PURCHASE_COLLECTION = "purchases"
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
