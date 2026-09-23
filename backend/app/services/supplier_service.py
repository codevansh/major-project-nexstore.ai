from datetime import datetime, timezone
<<<<<<< HEAD
=======

>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
from bson import ObjectId
from pymongo.database import Database

from app.models.supplier import supplier_document
<<<<<<< HEAD


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
=======
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class SupplierService:
    def __init__(self, db: Database):
        self.collection = db.suppliers

    def create_supplier(self, supplier: SupplierCreate) -> str:
        document = supplier_document(
            name=supplier.name,
            phone=supplier.phone,
            email=str(supplier.email) if supplier.email else None,
            address=supplier.address,
        )
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def get_supplier(self, supplier_id: str):
        if not ObjectId.is_valid(supplier_id):
            return None
        return self.collection.find_one({"_id": ObjectId(supplier_id)})

    def get_suppliers(self, skip: int = 0, limit: int = 50):
        return list(
            self.collection.find({"status": "active"})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

    def update_supplier(self, supplier_id: str, supplier: SupplierUpdate):
        if not ObjectId.is_valid(supplier_id):
            return None

        data = supplier.model_dump(exclude_unset=True)
        if "email" in data and data["email"] is not None:
            data["email"] = str(data["email"])

        contact_updates = {}
        for field in ("phone", "email"):
            if field in data:
                contact_updates[f"contact.{field}"] = data.pop(field)

        data.update(contact_updates)
        if not data:
            return self.get_supplier(supplier_id)

        data["updated_at"] = datetime.now(timezone.utc)
        self.collection.update_one(
            {"_id": ObjectId(supplier_id), "status": "active"},
            {"$set": data},
        )
        return self.get_supplier(supplier_id)

    def deactivate_supplier(self, supplier_id: str) -> bool:
        if not ObjectId.is_valid(supplier_id):
            return False

        result = self.collection.update_one(
            {"_id": ObjectId(supplier_id), "status": "active"},
            {
                "$set": {
                    "status": "inactive",
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )
        return result.modified_count > 0
>>>>>>> 44c87e5 (First 10 phases from the 27 phases are completed)
