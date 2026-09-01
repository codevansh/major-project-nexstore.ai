from datetime import datetime, timezone
from typing import Any


def product_document(
    sku: str,
    barcode:str,
    name: str,
    category: str,
    brand: str,
    cost_price: float,
    selling_price: float,
    description: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> dict:
    now = datetime.now(timezone.utc)

    return {
        "sku": sku,
        "barcode": barcode,
        "name": name,
        "category": category,
        "brand": brand,
        "description": description,
        "pricing": {
            "cost": cost_price,
            "selling": selling_price,
        },
        "attributes": attributes or {},
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
