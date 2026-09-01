from datetime import datetime, timezone


def inventory_document(
    product_id: str,
    store_id: str,
    available: int = 0,
    reserved: int = 0,
    damaged: int = 0,
    reorder_level: int = 10,
    reorder_quantity: int = 50,
) -> dict:

    now = datetime.now(timezone.utc)

    return {
        "product_id": product_id,
        "store_id": store_id,
        "stock": {
            "available": available,
            "reserved": reserved,
            "damaged": damaged,
        },
        "thresholds": {
            "reorder_level": reorder_level,
        },
        "reorder": {
            "recommended_quantity": reorder_quantity,
        },
        "updated_at": now,
    }
