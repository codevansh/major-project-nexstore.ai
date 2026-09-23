from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.models.purchase import purchase_document
from app.schemas.purchase import PurchaseCreate

from bson import ObjectId
from pymongo.database import Database

from app.models.purchase import PURCHASE_COLLECTION


class PurchaseService:
    def __init__(self, db: Database):

        self.db = db
        self.products = db.products
        self.inventory = db.inventory
        self.purchases = db.purchases
        self.suppliers = db.suppliers

    def create_purchase(self,purchase: PurchaseCreate):

        if not ObjectId.is_valid(
            purchase.supplier_id
        ):
            raise ValueError(
                "Invalid supplier ID."
            )

        supplier_id = ObjectId(
            purchase.supplier_id
        )
        supplier = self.suppliers.find_one(
            {
                "_id": supplier_id
            }
        )

        if supplier is None:
            raise ValueError(
                "Supplier not found."
            )

        existing_purchase = self.purchases.find_one(
            {
                "invoice_number":
                    purchase.invoice_number
            }
        )

        if existing_purchase:
            raise ValueError(
                "Purchase with this invoice number "
                "already exists."
            )

        purchase_items = []
        subtotal = 0.0

        for requested_item in purchase.items:
            product = self.products.find_one(
                {
                    "barcode": requested_item.barcode,
                    "status": "active",
                }
            )

            if product is None:
                raise ValueError(
                    "Product with barcode "
                    f"{requested_item.barcode} "
                    "was not found."
                )

            product_id = str(
                product["_id"]
            )
            item_subtotal = (
                requested_item.quantity
                * requested_item.unit_cost
            )
            subtotal += item_subtotal
            purchase_items.append(
                {
                    "product_id": product_id,
                    "barcode": product["barcode"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": requested_item.quantity,
                    "unit_cost": requested_item.unit_cost,
                    "subtotal": item_subtotal,
                }
            )

        if purchase.discount > subtotal:
            raise ValueError(
                "Discount cannot exceed subtotal."
            )

        total = (
            subtotal
            - purchase.discount
            + purchase.tax
        )

        client = self.db.client
        with client.start_session() as session:
            try:
                with session.start_transaction():
                    for item in purchase_items:
                        result = self.inventory.update_one(
                            {
                                "product_id":
                                    item["product_id"],

                                "store_id":
                                    purchase.store_id,
                            },

                            {
                                "$inc": {
                                    "stock.available":
                                        item["quantity"]
                                },

                                "$set": {
                                    "updated_at":
                                        datetime.now(
                                            timezone.utc
                                        )
                                }
                            },
                            session=session,
                        )

                        if result.matched_count == 0:
                            self.inventory.insert_one(
                                {
                                    "product_id":item["product_id"],
                                    "store_id":purchase.store_id,
                                    "stock": {
                                        "available":
                                            item["quantity"],

                                        "reserved": 0,
                                        "damaged": 0,
                                    },
                                    "thresholds": {
                                        "reorder_level":
                                            10
                                    },
                                    "reorder": {
                                        "recommended_quantity":
                                            50
                                    },

                                    "updated_at":
                                        datetime.now(
                                            timezone.utc
                                        )
                                },
                                session=session,
                            )

                    document = purchase_document(
                        invoice_number=purchase.invoice_number,
                        supplier_id=purchase.supplier_id,
                        store_id=purchase.store_id,
                        items=purchase_items,
                        subtotal=subtotal,
                        discount=purchase.discount,
                        tax=purchase.tax,
                        total=total,
                    )

                    result = self.purchases.insert_one(
                        document,
                        session=session,
                    )

                    purchase_id = result.inserted_id
                    self.suppliers.update_one(
                        {
                            "_id":supplier_id
                        },
                        {
                            "$inc": {
                                "purchase_summary.total_purchases":1,
                                "purchase_summary.total_purchase_value":total,
                            },
                            "$set": {
                                "updated_at":
                                    datetime.now(
                                        timezone.utc
                                    )
                            }
                        },
                        session=session
                    )

                return self.purchases.find_one(
                    {
                        "_id":
                            purchase_id
                    }
                )

            except DuplicateKeyError:
                raise ValueError(
                    "Purchase with this invoice number "
                    "already exists."
                )

    def get_purchase(self,purchase_id: str):
        if not ObjectId.is_valid(purchase_id):
            return None
        return self.purchases.find_one(
            {
                "_id":
                    ObjectId(purchase_id)
            }
        )

    def get_purchases(self,skip: int = 0,limit: int = 50):
        return list(
            self.purchases
            .find()
            .sort(
                "created_at",
                -1
            )
            .skip(skip)
            .limit(limit)
        )

        self.collection = db[ PURCHASE_COLLECTION ]

        self.collection = db[PURCHASE_COLLECTION]


    def get_purchases(self, skip: int = 0, limit: int = 50):
        return list(
            self.collection.find()
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )

    def get_purchase(self, purchase_id: str):
        if not ObjectId.is_valid(purchase_id):
            return None
        return self.collection.find_one({"_id": ObjectId(purchase_id)})

