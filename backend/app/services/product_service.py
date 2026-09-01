from bson import ObjectId
from pymongo.database import Database

from app.models.product import product_document
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
)


class ProductService:

    def __init__(self, db: Database):
        self.collection = db.products

    def create_product(self, product: ProductCreate) -> str:

        document = product_document(
            sku=product.sku,
            barcode=product.barcode,
            name=product.name,
            category=product.category,
            brand=product.brand,
            cost_price=product.cost_price,
            selling_price=product.selling_price,
            description=product.description,
            attributes=product.attributes,
        )
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def get_product(self, product_id: str):

        if not ObjectId.is_valid(product_id):
            return None
        return self.collection.find_one({"_id": ObjectId(product_id)})

    def get_products(self, skip: int = 0, limit: int = 50):

        return list(self.collection.find().skip(skip).limit(limit))

    def update_product(self, product_id: str, product: ProductUpdate):

        if not ObjectId.is_valid(product_id):
            return None

        update_data = {
            key: value for key, value in product.model_dump(exclude_unset=True).items()
        }

        if not update_data:
            return self.get_product(product_id)

        if "cost_price" in update_data:
            update_data["pricing.cost"] = update_data.pop("cost_price")

        if "selling_price" in update_data:
            update_data["pricing.selling"] = update_data.pop("selling_price")

        update_data["updated_at"] = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        )

        self.collection.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data},
        )

        return self.get_product(product_id)

    def delete_product(self, product_id: str) -> bool:
        if not ObjectId.is_valid(product_id):
            return False

        result = self.collection.delete_one({"_id": ObjectId(product_id)})

        return result.deleted_count > 0
