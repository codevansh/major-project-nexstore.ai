import math
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

    @staticmethod
    def _number(value) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        result = float(value)
        return result if math.isfinite(result) else None

    @classmethod
    def _line_revenue(cls, item: dict) -> float:
        subtotal = cls._number(item.get("subtotal"))
        if subtotal is not None:
            return subtotal
        quantity = cls._number(item.get("quantity"))
        unit_price = cls._number(item.get("unit_price"))
        if quantity is None or unit_price is None:
            return 0.0
        return quantity * unit_price

    @classmethod
    def _sale_revenue(cls, sale: dict) -> float:
        totals = sale.get("totals") or {}
        total = cls._number(totals.get("total"))
        if total is not None:
            return total

        subtotal = cls._number(totals.get("subtotal"))
        discount = cls._number(totals.get("discount")) or 0.0
        if subtotal is not None:
            return max(0.0, subtotal - discount)
        line_total = sum(
            cls._line_revenue(item)
            for item in (sale.get("items") or [])
            if isinstance(item, dict)
        )
        return max(0.0, line_total - discount)

    def _completed_sales(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> list[dict]:
        query: dict = {"status": "completed"}
        if store_id:
            query["store_id"] = store_id
        date_query = {}
        if start_date is not None:
            date_query["$gte"] = start_date
        if end_date is not None:
            date_query["$lte"] = end_date
        if date_query:
            query["created_at"] = date_query
        return list(self.sales.find(query))

    @classmethod
    def _product_breakdown(cls, sales: list[dict]) -> dict[str, dict]:
        products: dict[str, dict] = {}
        for sale in sales:
            seen_in_order: set[str] = set()
            sale_items = [
                item
                for item in (sale.get("items") or [])
                if isinstance(item, dict)
                and item.get("product_id")
                and (cls._number(item.get("quantity")) or 0) > 0
            ]
            gross_revenue = sum(cls._line_revenue(item) for item in sale_items)
            totals = sale.get("totals") or {}
            discount = cls._number(totals.get("discount")) or 0.0
            discount = min(max(discount, 0.0), gross_revenue)
            for item in sale_items:
                product_id = item.get("product_id")
                quantity = cls._number(item.get("quantity"))
                if not product_id or quantity is None or quantity <= 0:
                    continue

                product_id = str(product_id)
                row = products.setdefault(
                    product_id,
                    {
                        "product_id": product_id,
                        "product_name": item.get("name") or "Unknown product",
                        "barcode": item.get("barcode"),
                        "units_sold": 0,
                        "revenue": 0.0,
                        "order_count": 0,
                    },
                )
                row["units_sold"] += quantity
                line_revenue = cls._line_revenue(item)
                if gross_revenue:
                    line_revenue *= (gross_revenue - discount) / gross_revenue
                row["revenue"] += line_revenue
                if product_id not in seen_in_order:
                    row["order_count"] += 1
                    seen_in_order.add(product_id)
        return products

    @classmethod
    def _summary_from_sales(cls, sales: list[dict]) -> dict:
        revenue = sum(cls._sale_revenue(sale) for sale in sales)
        units = sum(
            number
            for sale in sales
            for item in (sale.get("items") or [])
            if isinstance(item, dict)
            for number in [cls._number(item.get("quantity"))]
            if number is not None and number > 0
        )
        count = len(sales)
        return {
            "revenue": round(revenue, 2),
            "units_sold": int(units),
            "order_count": count,
            "average_order_value": round(revenue / count, 2) if count else 0.0,
        }

    def get_sales_summary(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> dict:
        sales = self._completed_sales(start_date, end_date, store_id)
        return self._summary_from_sales(sales)

    def get_product_sales(
        self,
        product_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> dict:
        sales = self._completed_sales(start_date, end_date, store_id)
        row = self._product_breakdown(sales).get(product_id)
        if row is None:
            return {
                "product_id": product_id,
                "product_name": "Unknown product",
                "barcode": None,
                "units_sold": 0,
                "revenue": 0.0,
                "order_count": 0,
            }
        return {**row, "revenue": round(row["revenue"], 2)}

    def get_top_selling_products(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> list[dict]:
        rows = self._product_breakdown(
            self._completed_sales(start_date, end_date, store_id)
        ).values()
        ordered = sorted(
            rows,
            key=lambda row: (row["units_sold"], row["revenue"]),
            reverse=True,
        )
        return [
            {**row, "revenue": round(row["revenue"], 2)}
            for row in ordered[:limit]
        ]

    def get_low_performing_products(
        self,
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        store_id: str | None = None,
    ) -> list[dict]:
        sales = self._completed_sales(start_date, end_date, store_id)
        breakdown = self._product_breakdown(sales)
        if not sales:
            return []

        rows = dict(breakdown)
        for product in self.products.find({"status": "active"}):
            product_id = product.get("_id") or product.get("id")
            if product_id is None:
                continue
            product_id = str(product_id)
            if product_id not in rows:
                rows[product_id] = {
                    "product_id": product_id,
                    "product_name": product.get("name") or "Unknown product",
                    "barcode": product.get("barcode"),
                    "units_sold": 0,
                    "revenue": 0.0,
                    "order_count": 0,
                }
        ordered = sorted(
            rows.values(),
            key=lambda row: (row["units_sold"], row["revenue"], row["product_name"]),
        )
        return [
            {**row, "revenue": round(row["revenue"], 2)}
            for row in ordered[:limit]
        ]

    def compare_sales_periods(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        store_id: str | None = None,
    ) -> dict:
        current = self.get_sales_summary(current_start, current_end, store_id)
        previous = self.get_sales_summary(previous_start, previous_end, store_id)

        def percent_change(current_value: float, previous_value: float) -> float | None:
            if previous_value == 0:
                return None
            return round((current_value - previous_value) / previous_value * 100, 2)

        return {
            "current_period": current,
            "previous_period": previous,
            "revenue_change": round(current["revenue"] - previous["revenue"], 2),
            "revenue_change_percent": percent_change(
                current["revenue"], previous["revenue"]
            ),
            "units_change": current["units_sold"] - previous["units_sold"],
            "units_change_percent": percent_change(
                current["units_sold"], previous["units_sold"]
            ),
        }

    def compare_product_sales_periods(
        self,
        current_start: datetime,
        current_end: datetime,
        previous_start: datetime,
        previous_end: datetime,
        store_id: str | None = None,
    ) -> list[dict]:
        current_rows = self._product_breakdown(
            self._completed_sales(current_start, current_end, store_id)
        )
        previous_rows = self._product_breakdown(
            self._completed_sales(previous_start, previous_end, store_id)
        )
        product_ids = current_rows.keys() | previous_rows.keys()
        comparisons = []
        for product_id in product_ids:
            current = current_rows.get(product_id, {})
            previous = previous_rows.get(product_id, {})
            current_units = current.get("units_sold", 0)
            previous_units = previous.get("units_sold", 0)
            current_revenue = current.get("revenue", 0.0)
            previous_revenue = previous.get("revenue", 0.0)
            if current_revenue > previous_revenue:
                trend = "INCREASING"
            elif current_revenue < previous_revenue:
                trend = "DECLINING"
            elif current_units > previous_units:
                trend = "INCREASING"
            elif current_units < previous_units:
                trend = "DECLINING"
            else:
                trend = "STABLE"
            percent = (
                round((current_units - previous_units) / previous_units * 100, 2)
                if previous_units
                else None
            )
            comparisons.append(
                {
                    "product_id": product_id,
                    "product_name": current.get("product_name")
                    or previous.get("product_name")
                    or "Unknown product",
                    "current_units_sold": current_units,
                    "previous_units_sold": previous_units,
                    "current_revenue": round(current_revenue, 2),
                    "previous_revenue": round(previous_revenue, 2),
                    "units_change_percent": percent,
                    "trend": trend,
                }
            )
        return sorted(
            comparisons,
            key=lambda row: (
                row["trend"] != "DECLINING",
                row["current_revenue"] - row["previous_revenue"],
            ),
        )

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
