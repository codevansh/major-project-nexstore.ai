from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.core.config import settings

client = MongoClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=5000,
)

db: Database = client[settings.MONGODB_DATABASE]


def get_database() -> Database:
    return db


def test_database_connection() -> bool:
    try:
        client.admin.command("ping")
        return True
    except Exception:
        return False


def initialize_database() -> None:

    # Users
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="unique_user_email",
    )

    # Stores
    db.stores.create_index(
        [("store_code", ASCENDING)],
        unique=True,
        name="unique_store_code",
    )

    # Products
    db.products.create_index(
        [("sku", ASCENDING)],
        unique=True,
        name="unique_product_sku",
    )

    db.products.create_index(
        [("category", ASCENDING)],
        name="product_category_index",
    )

    db.products.create_index(
        [("brand", ASCENDING)],
        name="product_brand_index",
    )

    db.products.create_index(
        [("status", ASCENDING)],
        name="product_status_index",
    )

    db.products.create_index(
        [("barcode", ASCENDING)],
        unique=True,
        name="unique_product_barcode",
    )

    # Inventory
    db.inventory.create_index(
        [
            ("store_id", ASCENDING),
            ("product_id", ASCENDING),
        ],
        unique=True,
        name="unique_store_product_inventory",
    )

    db.inventory.create_index(
        [("stock.available", ASCENDING)],
        name="inventory_available_stock_index",
    )

    # Customers
    db.customers.create_index(
        [("contact.email", ASCENDING)],
        unique=True,
        sparse=True,
        name="unique_customer_email",
    )

    db.customers.create_index(
        [("segment", ASCENDING)],
        name="customer_segment_index",
    )

    # Sales
    db.sales.create_index(
        [("sale_date", DESCENDING)],
        name="sales_date_index",
    )

    db.sales.create_index(
        [("customer_id", ASCENDING)],
        name="sales_customer_index",
    )

    db.sales.create_index(
        [("store_id", ASCENDING)],
        name="sales_store_index",
    )

    db.sales.create_index(
        [("items.product_id", ASCENDING)],
        name="sales_product_index",
    )

    # Suppliers
    db.suppliers.create_index(
        [("supplier_code", ASCENDING)],
        unique=True,
        name="unique_supplier_code",
    )

    # Purchase Orders
    db.purchase_orders.create_index(
        [("order_date", DESCENDING)],
        name="purchase_order_date_index",
    )

    db.purchase_orders.create_index(
        [("supplier_id", ASCENDING)],
        name="purchase_order_supplier_index",
    )

    db.purchase_orders.create_index(
        [("status", ASCENDING)],
        name="purchase_order_status_index",
    )

    # AI Agent Runs
    db.agent_runs.create_index(
        [("created_at", DESCENDING)],
        name="agent_runs_date_index",
    )

    db.agent_runs.create_index(
        [("agent", ASCENDING)],
        name="agent_name_index",
    )

    db.agent_runs.create_index(
        [("status", ASCENDING)],
        name="agent_status_index",
    )

    # Recommendations
    db.recommendations.create_index(
        [("created_at", DESCENDING)],
        name="recommendations_date_index",
    )

    db.recommendations.create_index(
        [("status", ASCENDING)],
        name="recommendation_status_index",
    )

    db.recommendations.create_index(
        [("priority", ASCENDING)],
        name="recommendation_priority_index",
    )

    # Alerts
    db.alerts.create_index(
        [("created_at", DESCENDING)],
        name="alerts_date_index",
    )

    db.alerts.create_index(
        [("status", ASCENDING)],
        name="alert_status_index",
    )

    db.alerts.create_index(
        [("severity", ASCENDING)],
        name="alert_severity_index",
    )

    # Automation
    db.automation_tasks.create_index(
        [("created_at", DESCENDING)],
        name="automation_date_index",
    )

    db.automation_tasks.create_index(
        [("status", ASCENDING)],
        name="automation_status_index",
    )

    # System Events
    db.system_events.create_index(
        [("created_at", DESCENDING)],
        name="system_events_date_index",
    )
    
    # Purchases
    db.purchases.create_index(
    [("invoice_number", ASCENDING)],
    unique=True,
    name="unique_purchase_invoice",
    )

    db.purchases.create_index(
        [("supplier_id", ASCENDING)],
        name="purchase_supplier_index",
    )

    db.purchases.create_index(
        [("store_id", ASCENDING)],
        name="purchase_store_index",
    )

    db.purchases.create_index(
        [("created_at", DESCENDING)],
        name="purchase_date_index",
    )

    db.purchases.create_index(
        [("status", ASCENDING)],
        name="purchase_status_index",
    )
