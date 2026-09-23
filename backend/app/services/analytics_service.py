from datetime import datetime, timezone, timedelta

from pymongo.database import Database


class AnalyticsService:
    def __init__(self, db: Database):
        self.db = db
        self.products = db.products
        self.inventory = db.inventory
        self.sales = db.sales
        self.purchases = db.purchases
        self.customers = db.customers
        self.suppliers = db.suppliers
        self.expenses = db.expenses

    def get_overview(self):
        sales_result = list(self.sales.aggregate([
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": None,
                "total_sales": {"$sum": {"$toDouble": "$totals.total"}},
                "total_orders": {"$sum": 1},
            }},
        ]))
        purchases_result = list(self.purchases.aggregate([
            {"$match": {"status": "received"}},
            {"$group": {
                "_id": None,
                "total_purchase_value": {
                    "$sum": {"$toDouble": "$totals.total"}
                },
                "total_purchases": {"$sum": 1},
            }},
        ]))
        sales_data = sales_result[0] if sales_result else {}
        purchase_data = purchases_result[0] if purchases_result else {}
        total_products = self.products.count_documents({"status": "active"})
        total_customers = self.customers.count_documents({})
        total_suppliers = self.suppliers.count_documents({"status": "active"})
        inventory_result = list(self.inventory.aggregate([
            {"$group": {
                "_id": None,
                "total_available": {"$sum": "$stock.available"},
                "total_reserved": {"$sum": "$stock.reserved"},
                "total_damaged": {"$sum": "$stock.damaged"},
            }},
        ]))
        inventory_data = inventory_result[0] if inventory_result else {}
        return {
            "sales": {
                "total_sales": sales_data.get("total_sales", 0),
                "total_orders": sales_data.get("total_orders", 0),
            },
            "purchases": {
                "total_purchase_value": purchase_data.get("total_purchase_value", 0),
                "total_purchases": purchase_data.get("total_purchases", 0),
            },
            "inventory": {
                "total_available": inventory_data.get("total_available", 0),
                "total_reserved": inventory_data.get("total_reserved", 0),
                "total_damaged": inventory_data.get("total_damaged", 0),
            },
            "counts": {
                "products": total_products,
                "customers": total_customers,
                "suppliers": total_suppliers,
            },
        }

    def get_sales_analytics(self):
        result = list(self.sales.aggregate([
            {"$match": {"status": "completed"}},
            {"$group": {
                "_id": None,
                "total_sales": {"$sum": {"$toDouble": "$totals.total"}},
                "total_orders": {"$sum": 1},
                "average_order_value": {"$avg": {"$toDouble": "$totals.total"}},
                "total_discount": {"$sum": {"$toDouble": "$totals.discount"}},
            }},
        ]))
        if not result:
            return {
                "total_sales": 0,
                "total_orders": 0,
                "average_order_value": 0,
                "total_discount": 0,
            }
        data = result[0]
        return {
            "total_sales": data.get("total_sales", 0),
            "total_orders": data.get("total_orders", 0),
            "average_order_value": data.get("average_order_value", 0),
            "total_discount": data.get("total_discount", 0),
        }

    def get_top_products(self, limit: int = 10):
        result = self.sales.aggregate([
            {"$match": {"status": "completed"}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.product_id",
                "product_name": {"$first": "$items.name"},
                "barcode": {"$first": "$items.barcode"},
                "quantity_sold": {"$sum": "$items.quantity"},
                "revenue": {
                    "$sum": {"$multiply": ["$items.quantity", "$items.unit_price"]}
                },
            }},
            {"$sort": {"quantity_sold": -1}},
            {"$limit": limit},
        ])
        return list(result)

    def get_low_stock(self):
        result = self.inventory.aggregate([
            {"$match": {"$expr": {
                "$lte": ["$stock.available", "$thresholds.reorder_level"]
            }}},
            {"$lookup": {
                "from": "products",
                "let": {"product_id": "$product_id"},
                "pipeline": [{"$match": {"$expr": {
                    "$eq": [{"$toString": "$_id"}, "$$product_id"]
                }}}],
                "as": "product",
            }},
            {"$unwind": {
                "path": "$product",
                "preserveNullAndEmptyArrays": True,
            }},
            {"$project": {
                "_id": 0,
                "product_id": 1,
                "store_id": 1,
                "available": "$stock.available",
                "reorder_level": "$thresholds.reorder_level",
                "reorder_quantity": "$reorder.recommended_quantity",
                "product_name": "$product.name",
                "barcode": "$product.barcode",
            }},
        ])
        return list(result)

    def get_inventory_analytics(self):
        result = list(self.inventory.aggregate([
            {"$group": {
                "_id": None,
                "total_available": {"$sum": "$stock.available"},
                "total_reserved": {"$sum": "$stock.reserved"},
                "total_damaged": {"$sum": "$stock.damaged"},
                "total_inventory_items": {"$sum": 1},
            }},
        ]))
        if not result:
            return {
                "total_available": 0,
                "total_reserved": 0,
                "total_damaged": 0,
                "total_inventory_items": 0,
            }
        data = result[0]
        return {
            "total_available": data.get("total_available", 0),
            "total_reserved": data.get("total_reserved", 0),
            "total_damaged": data.get("total_damaged", 0),
            "total_inventory_items": data.get("total_inventory_items", 0),
        }

    def get_product_analytics(self):
        categories = list(self.products.aggregate([
            {"$group": {"_id": "$category", "product_count": {"$sum": 1}}},
            {"$sort": {"product_count": -1}},
        ]))
        return {
            "total_products": self.products.count_documents({}),
            "active_products": self.products.count_documents({"status": "active"}),
            "inactive_products": self.products.count_documents({"status": {"$ne": "active"}}),
            "categories": [
                {"category": item["_id"], "product_count": item["product_count"]}
                for item in categories
            ],
        }

    def get_customer_analytics(self):
        segments = list(self.customers.aggregate([
            {"$group": {"_id": "$segment", "customer_count": {"$sum": 1}}},
            {"$sort": {"customer_count": -1}},
        ]))
        spending_result = list(self.customers.aggregate([
            {"$group": {
                "_id": None,
                "total_spent": {"$sum": "$purchase_summary.total_spent"},
                "total_orders": {"$sum": "$purchase_summary.total_orders"},
            }},
        ]))
        spending_data = spending_result[0] if spending_result else {}
        return {
            "total_customers": self.customers.count_documents({}),
            "total_spent": spending_data.get("total_spent", 0),
            "total_orders": spending_data.get("total_orders", 0),
            "segments": [
                {"segment": item["_id"], "customer_count": item["customer_count"]}
                for item in segments
            ],
        }

    @staticmethod
    def _amount(document: dict, paths: tuple[str, ...]) -> float:
        for path in paths:
            value = document
            for part in path.split("."):
                if not isinstance(value, dict) or part not in value:
                    value = None
                    break
                value = value[part]
            if isinstance(value, (int, float)):
                return float(value)
        return 0.0

    @staticmethod
    def _query(
        store_id: str | None,
        date_field: str,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> dict:
        query: dict = {}
        if store_id:
            query["store_id"] = store_id
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query[date_field] = date_query
        return query

    def get_finance_summary(
        self,
        store_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        sales_query = self._query(store_id, "created_at", start_date, end_date)
        purchase_query = self._query(store_id, "created_at", start_date, end_date)
        expense_query = self._query(store_id, "expense_date", start_date, end_date)
        expense_query["status"] = "active"
        total_revenue = sum(
            self._amount(sale, ("totals.total",))
            for sale in self.sales.find({**sales_query, "status": "completed"})
        )
        total_purchases = sum(
            self._amount(
                purchase,
                ("totals.total", "totals.total_cost", "total_cost", "total"),
            )
            for purchase in self.purchases.find(purchase_query)
        )
        total_expenses = sum(
            self._amount(expense, ("amount",))
            for expense in self.expenses.find(expense_query)
        )
        gross_profit = total_revenue - total_purchases
        return {
            "total_revenue": total_revenue,
            "total_purchases": total_purchases,
            "total_expenses": total_expenses,
            "gross_profit": gross_profit,
            "net_profit": gross_profit - total_expenses,
        }
