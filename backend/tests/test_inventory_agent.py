import unittest
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from app.agents.inventory_agent import InventoryIntelligenceAgent
from app.schemas.inventory_agent import InventoryAgentRequest
from app.services.inventory_intelligence_service import InventoryIntelligenceTools


class FakeCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, query=None, projection=None):
        query = query or {}
        return [doc for doc in self.documents if self._matches(doc, query)]

    def find_one(self, query):
        return next(
            (doc for doc in self.documents if self._matches(doc, query)),
            None,
        )

    @classmethod
    def _matches(cls, document, query):
        for key, value in query.items():
            if key == "items.product_id":
                if not any(item.get("product_id") == value for item in document.get("items", [])):
                    return False
            elif document.get(key) != value:
                return False
        return True


class FakeDatabase:
    def __init__(self, inventory, products, sales):
        self.inventory = FakeCollection(inventory)
        self.products = FakeCollection(products)
        self.sales = FakeCollection(sales)


class BrokenLLM:
    def invoke(self, _input):
        raise RuntimeError("model is offline")


class InventoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, tzinfo=timezone.utc)
        self.product_id = str(ObjectId())
        self.inventory = {
            "product_id": self.product_id,
            "store_id": "store-1",
            "stock": {"available": 4, "reserved": 0, "damaged": 0},
            "thresholds": {"reorder_level": 5},
            "reorder": {"recommended_quantity": 12},
        }
        self.product = {"_id": ObjectId(self.product_id), "name": "Tea", "sku": "TEA-1"}

    def _sales(self, quantities=(30, 30, 30)):
        return [
            {
                "status": "completed",
                "store_id": "store-1",
                "created_at": self.now - timedelta(days=days_ago),
                "items": [{"product_id": self.product_id, "quantity": quantity}],
            }
            for days_ago, quantity in zip((20, 10, 2), quantities)
        ]

    def _agent(self, sales, *, llm=None, inventory=None):
        db = FakeDatabase(
            [inventory or self.inventory],
            [self.product],
            sales,
        )
        tools = InventoryIntelligenceTools(db, now=self.now)
        return InventoryIntelligenceAgent(db, tools=tools, llm=llm)

    def test_forecast_uses_completed_sales_history(self):
        agent = self._agent(self._sales())
        forecast = agent.tools.get_demand_forecast(
            self.product_id,
            7,
            "store-1",
        )

        self.assertEqual(forecast["history_units"], 90)
        self.assertEqual(forecast["average_daily_demand"], 1.0)
        self.assertEqual(forecast["predicted_units"], 7)
        self.assertEqual(forecast["method"], "historical_average")

    def test_insufficient_history_does_not_create_a_forecast(self):
        agent = self._agent(self._sales(quantities=(4,))[:1])
        forecast = agent.tools.get_demand_forecast(
            self.product_id,
            7,
            "store-1",
        )

        self.assertIsNone(forecast["predicted_units"])
        self.assertEqual(forecast["method"], "unavailable")

    def test_low_stock_recommendation_is_data_grounded_and_requires_approval(self):
        result = self._agent(self._sales()).run(
            InventoryAgentRequest(
                question="Which products should I reorder this week?",
                store_id="store-1",
            )
        )

        recommendation = result["recommendations"][0]
        self.assertEqual(recommendation["product_id"], self.product_id)
        self.assertEqual(recommendation["current_stock"], 4)
        self.assertEqual(recommendation["predicted_demand"], 7)
        self.assertEqual(recommendation["recommended_reorder_quantity"], 12)
        self.assertEqual(recommendation["inventory_status"], "LOW_STOCK")
        self.assertTrue(recommendation["requires_human_approval"])
        self.assertTrue(result["human_approval_required"])

    def test_llm_failure_falls_back_to_deterministic_answer(self):
        result = self._agent(self._sales(), llm=BrokenLLM()).run(
            InventoryAgentRequest(question="Check stock", store_id="store-1")
        )

        self.assertIn("Tea", result["answer"])
        self.assertEqual(result["recommendations"][0]["current_stock"], 4)

    def test_overstock_is_identified_from_calculated_coverage(self):
        inventory = {
            **self.inventory,
            "stock": {"available": 10, "reserved": 0, "damaged": 0},
            "thresholds": {"reorder_level": 2},
        }
        result = self._agent(self._sales(quantities=(1, 1, 1)), inventory=inventory).run(
            InventoryAgentRequest(question="Check excess stock", store_id="store-1")
        )

        recommendation = result["recommendations"][0]
        self.assertEqual(recommendation["inventory_status"], "OVERSTOCK")
        self.assertEqual(recommendation["recommended_reorder_quantity"], 0)


if __name__ == "__main__":
    unittest.main()
