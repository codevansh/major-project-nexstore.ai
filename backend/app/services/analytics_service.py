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


    def get_overview(self):
        sales_result = list(
            self.sales.aggregate(
                [
                    {
                        "$match": {
                            "status": "completed"
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "total_sales": {
                                "$sum": {
                                    "$toDouble": "$totals.total"
                                }
                            },
                            "total_orders": {
                                "$sum": 1
                            }
                        }
                    }
                ]
            )
        )

        purchases_result = list(
            self.purchases.aggregate(
                [
                    {
                        "$match": {
                            "status": "received"
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "total_purchase_value": {
                                    "$sum": {
                                        "$toDouble": "$totals.total"
                                    }
                                },
                            "total_purchases": {
                                "$sum": 1
                            }
                        }
                    }
                ]
            )
        )

        sales_data = (
            sales_result[0]
            if sales_result
            else {}
        )

        purchase_data = (
            purchases_result[0]
            if purchases_result
            else {}
        )

        total_products = self.products.count_documents(
            {
                "status": "active"
            }
        )

        total_customers = self.customers.count_documents({})
        total_suppliers = self.suppliers.count_documents(
            {
                "status": "active"
            }
        )

        inventory_result = list(
            self.inventory.aggregate(
                [
                    {
                        "$group": {
                            "_id": None,
                            "total_available": {
                                "$sum":
                                    "$stock.available"
                            },
                            "total_reserved": {
                                "$sum":
                                    "$stock.reserved"
                            },
                            "total_damaged": {
                                "$sum":
                                    "$stock.damaged"
                            }
                        }
                    }
                ]
            )
        )

        inventory_data = (
            inventory_result[0]
            if inventory_result
            else {}
        )

        return {
            "sales": {
                "total_sales": sales_data.get(
                    "total_sales",
                    0
                ),
                "total_orders": sales_data.get(
                    "total_orders",
                    0
                ),
            },

            "purchases": {
                "total_purchase_value":
                    purchase_data.get(
                        "total_purchase_value",
                        0
                    ),

                "total_purchases":
                    purchase_data.get(
                        "total_purchases",
                        0
                    ),
            },

            "inventory": {
                "total_available":
                    inventory_data.get(
                        "total_available",
                        0
                    ),

                "total_reserved":
                    inventory_data.get(
                        "total_reserved",
                        0
                    ),

                "total_damaged":
                    inventory_data.get(
                        "total_damaged",
                        0
                    ),
            },

            "counts": {
                "products":
                    total_products,

                "customers":
                    total_customers,

                "suppliers":
                    total_suppliers,
            }
        }


    def get_sales_analytics(self):
        result = list(
            self.sales.aggregate(
                [
                    {
                        "$match": {
                            "status": "completed"
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                           "total_sales": {
                                "$sum": {
                                    "$toDouble": "$totals.total"
                                }
                            },
                            "total_orders": {
                                "$sum": 1
                            },
                            "average_order_value": {
                                "$avg": {
                                    "$toDouble": "$totals.total"
                                }
                            },
                            "total_discount": {
                                "$sum": {
                                    "$toDouble": "$totals.discount"
                                }
                            }
                        }
                    }
                ]
            )
        )

        if not result:
            return {
                "total_sales": 0,
                "total_orders": 0,
                "average_order_value": 0,
                "total_discount": 0,
            }

        data = result[0]

        return {
            "total_sales":
                data.get(
                    "total_sales",
                    0
                ),

            "total_orders":
                data.get(
                    "total_orders",
                    0
                ),

            "average_order_value":
                data.get(
                    "average_order_value",
                    0
                ),

            "total_discount":
                data.get(
                    "total_discount",
                    0
                ),
        }


    def get_top_products(
        self,
        limit: int = 10
    ):

        result = self.sales.aggregate(
            [
                {
                    "$match": {
                        "status": "completed"
                    }
                },

                {
                    "$unwind": "$items"
                },

                {
                    "$group": {
                        "_id":
                            "$items.product_id",

                        "product_name": {
                            "$first":
                                "$items.name"
                        },

                        "barcode": {
                            "$first":
                                "$items.barcode"
                        },

                        "quantity_sold": {
                            "$sum":
                                "$items.quantity"
                        },

                        "revenue": {
                            "$sum": {
                                "$multiply": [
                                    "$items.quantity",
                                    "$items.unit_price"
                                ]
                            }
                        }
                    }
                },

                {
                    "$sort": {
                        "quantity_sold": -1
                    }
                },

                {
                    "$limit": limit
                }
            ]
        )

        return list(result)


    def get_low_stock(self):
        result = self.inventory.aggregate(
            [
                {
                    "$match": {
                        "$expr": {
                            "$lte": [
                                "$stock.available",
                                "$thresholds.reorder_level"
                            ]
                        }
                    }
                },

                {
                    "$lookup": {
                        "from": "products",
                        "let": {
                            "product_id":
                                "$product_id"
                        },

                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [
                                            {
                                                "$toString":"$_id"
                                            },
                                            "$$product_id"
                                        ]
                                    }
                                }
                            }
                        ],

                        "as": "product"
                    }
                },

                {
                    "$unwind": {
                        "path":
                            "$product",

                        "preserveNullAndEmptyArrays":
                            True
                    }
                },

                {
                    "$project": {
                        "_id": 0,
                        "product_id": 1,
                        "store_id": 1,
                        "available":"$stock.available",
                        "reorder_level":"$thresholds.reorder_level",
                        "reorder_quantity":"$reorder.recommended_quantity",
                        "product_name":"$product.name",
                        "barcode":"$product.barcode"
                    }
                }
            ]
        )

        return list(result)