from datetime import datetime, timezone
from bson import ObjectId
from pymongo.database import Database

from app.models.supplier import supplier_document


def create_supplier(
    db: Database,
    name: str,
    phone: str | None = None,
    email: str | None = None,
    address: str | None = None,
) -> dict:

    document = supplier_document(
        name=name,
        phone=phone,
        email=email,
        address=address,
    )

    result = db.suppliers.insert_one(document)
    document["_id"] = result.inserted_id
    return document


def get_supplier(
    db: Database,
    supplier_id: str,
) -> dict | None:

    if not ObjectId.is_valid(supplier_id):
        return None

    return db.suppliers.find_one({
        "_id": ObjectId(supplier_id)
    })


def get_suppliers(
    db: Database,
) -> list[dict]:

    return list(
        db.suppliers.find().sort("created_at", -1)
    )


def update_supplier(
    db: Database,
    supplier_id: str,
    updates: dict,
) -> dict | None:

    if not ObjectId.is_valid(supplier_id):
        return None
    updates["updated_at"] = datetime.now(timezone.utc)
    result = db.suppliers.find_one_and_update(
        {"_id": ObjectId(supplier_id)},
        {"$set": updates},
        return_document=True,
    )

    return result


def delete_supplier(
    db: Database,
    supplier_id: str,
) -> bool:

    if not ObjectId.is_valid(supplier_id):
        return False
    result = db.suppliers.delete_one({
        "_id": ObjectId(supplier_id)
    })
    return result.deleted_count == 1