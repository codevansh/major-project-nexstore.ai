from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from app.models.inventory import inventory_document
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
)


class InventoryService:

    def __init__(self, db: Database):
        self.collection = db.inventory

    def create_inventory(
        self,
        inventory: InventoryCreate,
    ) -> str:

        document = inventory_document(
            product_id=inventory.product_id,
            store_id=inventory.store_id,
            available=inventory.available,
            reserved=inventory.reserved,
            damaged=inventory.damaged,
            reorder_level=inventory.reorder_level,
            reorder_quantity=inventory.reorder_quantity,
        )

        result = self.collection.insert_one(document)

        return str(result.inserted_id)

    def get_inventory(
        self,
        inventory_id: str,
    ):

        if not ObjectId.is_valid(inventory_id):
            return None

        return self.collection.find_one({"_id": ObjectId(inventory_id)})

    def get_inventory_by_product(
        self,
        product_id: str,
        store_id: str,
    ):

        return self.collection.find_one(
            {
                "product_id": product_id,
                "store_id": store_id,
            }
        )

    def get_all_inventory(
        self,
        skip: int = 0,
        limit: int = 50,
    ):

        return list(self.collection.find().skip(skip).limit(limit))

    def update_inventory(
        self,
        inventory_id: str,
        inventory: InventoryUpdate,
    ):

        if not ObjectId.is_valid(inventory_id):
            return None

        update_data = inventory.model_dump(exclude_unset=True)

        if not update_data:
            return self.get_inventory(inventory_id)

        field_mapping = {
            "available": "stock.available",
            "reserved": "stock.reserved",
            "damaged": "stock.damaged",
            "reorder_level": "thresholds.reorder_level",
            "reorder_quantity": "reorder.recommended_quantity",
        }

        mongo_update = {}

        for field, value in update_data.items():
            mongo_update[field_mapping[field]] = value

        mongo_update["updated_at"] = datetime.now(timezone.utc)

        self.collection.update_one(
            {"_id": ObjectId(inventory_id)},
            {"$set": mongo_update},
        )

        return self.get_inventory(inventory_id)

    def delete_inventory(
        self,
        inventory_id: str,
    ) -> bool:

        if not ObjectId.is_valid(inventory_id):
            return False

        result = self.collection.delete_one({"_id": ObjectId(inventory_id)})

        return result.deleted_count > 0
