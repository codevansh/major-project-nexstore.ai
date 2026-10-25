import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from bson import ObjectId

from app.api.purchases import get_purchases
from app.models.purchase import PURCHASE_COLLECTION
from app.services.analytics_service import AnalyticsService
from app.services.purchase_service import PurchaseService


class PurchaseServiceTests(unittest.TestCase):
    def test_get_purchases_uses_purchases_collection_and_pagination(self):
        rows = [{"_id": "newest"}, {"_id": "older"}]
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__iter__ = Mock(return_value=iter(rows))
        collection = Mock()
        collection.find.return_value = cursor
        db = _FakeDatabase({PURCHASE_COLLECTION: collection})
        service = PurchaseService(db)

        self.assertEqual(service.get_purchases(skip=10, limit=5), rows)
        db.collection.assert_called_once_with(PURCHASE_COLLECTION)
        collection.find.assert_called_once_with()
        cursor.sort.assert_called_once_with("created_at", -1)
        cursor.skip.assert_called_once_with(10)
        cursor.limit.assert_called_once_with(5)

    def test_get_purchase_uses_the_same_purchases_collection(self):
        purchase_id = ObjectId()
        purchase = {"_id": purchase_id, "invoice_number": "INV-2"}
        collection = Mock()
        collection.find_one.return_value = purchase
        db = _FakeDatabase({PURCHASE_COLLECTION: collection})
        service = PurchaseService(db)

        self.assertEqual(service.get_purchase(str(purchase_id)), purchase)
        db.collection.assert_called_once_with(PURCHASE_COLLECTION)
        collection.find_one.assert_called_once_with({"_id": purchase_id})


class PurchaseEndpointTests(unittest.TestCase):
    def test_list_endpoint_returns_purchase_response_shape(self):
        purchase = {
            "_id": "purchase-id",
            "invoice_number": "INV-1",
            "supplier_id": "supplier-id",
            "store_id": "STORE-001",
            "items": [],
            "totals": {"subtotal": 10, "discount": 1, "tax": 2, "total": 11},
            "status": "received",
        }
        service = Mock()
        service.get_purchases.return_value = [purchase]
        result = get_purchases(skip=2, limit=7, service=service)

        self.assertEqual(result, [{
            "id": "purchase-id",
            "invoice_number": "INV-1",
            "supplier_id": "supplier-id",
            "store_id": "STORE-001",
            "items": [],
            "subtotal": 10,
            "discount": 1,
            "tax": 2,
            "total": 11,
            "status": "received",
        }])
        service.get_purchases.assert_called_once_with(skip=2, limit=7)


class FinanceSummaryTests(unittest.TestCase):
    def make_collection(self, documents):
        collection = Mock()
        collection.find.side_effect = lambda query: documents
        collection.find_one.side_effect = lambda query: {
            "pricing": {"cost": 40}
        } if query.get("_id") == "legacy-product" else None
        return collection

    def test_profit_uses_cost_of_sold_items_not_total_inventory_purchases(self):
        sales = self.make_collection([
            {
                "status": "completed",
                "totals": {"total": 200},
                "items": [{"product_id": "snapshotted", "quantity": 2, "unit_cost": 30}],
            },
            {
                "status": "completed",
                "totals": {"total": 100},
                "items": [{"product_id": "legacy-product", "quantity": 1}],
            },
        ])
        purchases = self.make_collection([
            {"status": "received", "totals": {"total": 500}},
        ])
        expenses = self.make_collection([{"amount": 20, "status": "active"}])
        products = self.make_collection([])
        service = AnalyticsService(SimpleNamespace(
            sales=sales,
            purchases=purchases,
            expenses=expenses,
            products=products,
            inventory=Mock(),
            customers=Mock(),
            suppliers=Mock(),
        ))

        result = service.get_finance_summary()

        self.assertEqual(result["total_revenue"], 300)
        self.assertEqual(result["total_purchases"], 500)
        self.assertEqual(result["cost_of_goods_sold"], 100)
        self.assertEqual(result["total_expenses"], 20)
        self.assertEqual(result["gross_profit"], 200)
        self.assertEqual(result["net_profit"], 180)
        self.assertEqual(purchases.find.call_args.args[0], {"status": "received"})

    def test_empty_finance_data_returns_zero_totals(self):
        empty = self.make_collection([])
        service = AnalyticsService(SimpleNamespace(
            sales=empty,
            purchases=empty,
            expenses=empty,
            products=empty,
            inventory=Mock(),
            customers=Mock(),
            suppliers=Mock(),
        ))

        result = service.get_finance_summary()

        self.assertEqual(result["cost_of_goods_sold"], 0)
        self.assertEqual(result["gross_profit"], 0)
        self.assertEqual(result["net_profit"], 0)


class _FakeDatabase:
    def __init__(self, collections):
        self._collections = collections
        self.products = Mock()
        self.inventory = Mock()
        self.suppliers = Mock()
        self.collection = Mock()

    def __getitem__(self, name):
        self.collection(name)
        return self._collections[name]


if __name__ == "__main__":
    unittest.main()
