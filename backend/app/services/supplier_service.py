from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.models.supplier import supplier_document
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
