from datetime import datetime, timezone
from uuid import uuid4

from bson import ObjectId
from pymongo.database import Database

from app.models.sale import sale_document
from app.schemas.sale import (
    BarcodeScanRequest,
    SaleCheckoutRequest,
)


class SalesService:

    def __init__(self, db: Database):
        self.db = db

        self.products = db.products
        self.inventory = db.inventory
        self.sales = db.sales
        self.customers = db.customers

    # BARCODE SCAN

    def scan_barcode(
        self,
        request: BarcodeScanRequest,
    ):

        product = self.products.find_one(
            {
                "barcode": request.barcode,
                "status": "active",
            }
        )

        if product is None:
            return {
                "success": False,
                "reason": "product_not_found",
            }

        inventory = self.inventory.find_one(
            {
                "product_id": str(product["_id"]),
                "store_id": request.store_id,
            }
        )

        if inventory is None:
            return {
                "success": False,
                "reason": "inventory_not_found",
                "product_id": str(product["_id"]),
            }

        available = inventory["stock"]["available"]

        return {
            "success": True,
            "product": {
                "id": str(product["_id"]),
                "sku": product["sku"],
                "barcode": product["barcode"],
                "name": product["name"],
                "category": product["category"],
                "brand": product["brand"],
                "selling_price": product["pricing"]["selling"],
            },
            "inventory": {
                "available": available,
                "requested": request.quantity,
                "can_purchase": (available >= request.quantity),
            },
        }

    # CHECKOUT
    def checkout(
        self,
        request: SaleCheckoutRequest,
    ):
        sale_items = []
        subtotal = 0.0

        # Validate every scanned product first
        for requested_item in request.items:
            product = self.products.find_one(
                {
                    "barcode": requested_item.barcode,
                    "status": "active",
                }
            )

            if product is None:
                raise ValueError(
                    f"Product with barcode "
                    f"{requested_item.barcode} "
                    f"was not found."
                )

            product_id = str(product["_id"])
            inventory = self.inventory.find_one(
                {
                    "product_id": product_id,
                    "store_id": request.store_id,
                }
            )

            if inventory is None:
                raise ValueError(f"No inventory exists for " f"{product['name']}.")

            available = inventory["stock"]["available"]

            if available < requested_item.quantity:
                raise ValueError(
                    f"Insufficient stock for "
                    f"{product['name']}. "
                    f"Available: {available}, "
                    f"requested: "
                    f"{requested_item.quantity}."
                )
            unit_price = float(product["pricing"]["selling"])
            item_subtotal = unit_price * requested_item.quantity
            subtotal += item_subtotal
            sale_items.append(
                {
                    "product_id": product_id,
                    "barcode": product["barcode"],
                    "sku": product["sku"],
                    "name": product["name"],
                    "quantity": requested_item.quantity,
                    "unit_price": unit_price,
                    "subtotal": item_subtotal,
                }
            )

        # Calculate final amount
        if request.discount > subtotal:
            raise ValueError("Discount cannot exceed subtotal.")
        total = subtotal - request.discount

        # Deduct inventory atomically
        for item in sale_items:
            result = self.inventory.update_one(
                {
                    "product_id": item["product_id"],
                    "store_id": request.store_id,
                    "stock.available": {"$gte": item["quantity"]},
                },
                {
                    "$inc": {"stock.available": -item["quantity"]},
                    "$set": {"updated_at": datetime.now(timezone.utc)},
                },
            )

            if result.modified_count == 0:
                raise ValueError(
                    f"Stock changed while processing "
                    f"{item['name']}. "
                    f"Please retry the transaction."
                )

        # Generate invoice

        invoice_number = (
            "NS-" + datetime.now().strftime("%Y%m%d") + "-" + uuid4().hex[:8].upper()
        )

        document = sale_document(
            invoice_number=invoice_number,
            store_id=request.store_id,
            customer_id=request.customer_id,
            items=sale_items,
            subtotal=subtotal,
            discount=request.discount,
            total=total,
            payment_method=request.payment_method,
        )
        result = self.sales.insert_one(document)
        sale_id = str(result.inserted_id)

        # Update customer statistics

        if request.customer_id:
            if ObjectId.is_valid(request.customer_id):
                self.customers.update_one(
                    {"_id": ObjectId(request.customer_id)},
                    {
                        "$inc": {
                            "purchase_summary.total_orders": 1,
                            "purchase_summary.total_spent": total,
                        },
                        "$set": {"updated_at": datetime.now(timezone.utc)},
                    },
                )

                customer = self.customers.find_one(
                    {"_id": ObjectId(request.customer_id)}
                )

                if customer:
                    summary = customer["purchase_summary"]
                    total_orders = summary["total_orders"]
                    total_spent = summary["total_spent"]
                    average_order_value = total_spent / total_orders

                    # Simple first-stage
                    # customer segmentation
                    if total_orders >= 10:
                        segment = "loyal"
                    elif total_spent >= 25000:
                        segment = "high_value"
                    elif total_orders >= 3:
                        segment = "regular"
                    else:
                        segment = "new"

                    self.customers.update_one(
                        {"_id": ObjectId(request.customer_id)},
                        {
                            "$set": {
                                "purchase_summary.average_order_value": average_order_value,
                                "segment": segment,
                                "updated_at": datetime.now(timezone.utc),
                            }
                        },
                    )

        return self.sales.find_one({"_id": ObjectId(sale_id)})

    # GET SALE
    def get_sale(
        self,
        sale_id: str,
    ):

        if not ObjectId.is_valid(sale_id):
            return None

        return self.sales.find_one({"_id": ObjectId(sale_id)})

    # GET ALL SALES
    def get_sales(
        self,
        skip: int = 0,
        limit: int = 50,
    ):

        return list(self.sales.find().sort("created_at", -1).skip(skip).limit(limit))
