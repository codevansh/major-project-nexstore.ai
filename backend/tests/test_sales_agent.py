import unittest
from datetime import datetime, timezone

from app.agents.sales_agent import SalesIntelligenceAgent
from app.schemas.sales_agent import SalesAgentRequest
from app.services.analytics_service import AnalyticsService
from tests.sales_fakes import FakeDatabase


NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
CURRENT_START = datetime(2026, 10, 3, tzinfo=timezone.utc)
CURRENT_END = NOW
PREVIOUS_SALE_DATE = datetime(2026, 10, 1, tzinfo=timezone.utc)


def sale(day, invoice, total, items, *, store_id="store-1", totals=True):
    document = {
        "status": "completed",
        "store_id": store_id,
        "created_at": datetime(2026, 10, day, tzinfo=timezone.utc),
        "invoice_number": invoice,
        "items": items,
    }
    if totals:
        document["totals"] = {"total": total, "discount": 0}
    return document


def example_database():
    sales = [
        sale(9, "CUR-A1", 30, [{"product_id": "p1", "name": "Tea", "quantity": 3, "unit_price": 10, "subtotal": 30}]),
        sale(8, "CUR-A2", 20, [{"product_id": "p1", "name": "Tea", "quantity": 2, "unit_price": 10, "subtotal": 20}]),
        sale(1, "PREV-A", 100, [{"product_id": "p1", "name": "Tea", "quantity": 10, "unit_price": 10, "subtotal": 100}]),
        sale(9, "CUR-B", 40, [{"product_id": "p2", "name": "Coffee", "quantity": 2, "unit_price": 20, "subtotal": 40}]),
        sale(1, "PREV-B", 20, [{"product_id": "p2", "name": "Coffee", "quantity": 1, "unit_price": 20, "subtotal": 20}]),
        sale(9, "OTHER-STORE", 500, [{"product_id": "p1", "name": "Tea", "quantity": 50, "unit_price": 10, "subtotal": 500}], store_id="store-2"),
        sale(9, "VOID", 900, [{"product_id": "p1", "name": "Tea", "quantity": 90, "unit_price": 10, "subtotal": 900}], totals=True),
    ]
    sales[-1]["status"] = "void"
    products = [
        {"_id": "p1", "name": "Tea", "status": "active"},
        {"_id": "p2", "name": "Coffee", "status": "active"},
        {"_id": "p3", "name": "Biscuits", "status": "active"},
    ]
    return FakeDatabase(sales, products)


class SalesAnalyticsServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = example_database()
        self.service = AnalyticsService(self.db)

    def test_summary_uses_completed_store_sales_and_handles_missing_totals(self):
        records = [
            sale(9, "A", 0, [{"product_id": "p1", "quantity": 2, "unit_price": 5}], totals=False),
        ]
        db = FakeDatabase(records)
        result = AnalyticsService(db).get_sales_summary(
            datetime(2026, 10, 3, tzinfo=timezone.utc),
            NOW,
            "store-1",
        )
        self.assertEqual(result["revenue"], 10)
        self.assertEqual(result["units_sold"], 2)
        self.assertEqual(result["average_order_value"], 10)

    def test_period_comparison_calculates_real_percent_change(self):
        result = self.service.compare_sales_periods(
            CURRENT_START,
            CURRENT_END,
            datetime(2026, 9, 26, tzinfo=timezone.utc),
            datetime(2026, 10, 2, tzinfo=timezone.utc),
            "store-1",
        )
        self.assertEqual(result["current_period"]["revenue"], 90)
        self.assertEqual(result["previous_period"]["revenue"], 120)
        self.assertEqual(result["revenue_change_percent"], -25)

    def test_top_and_low_products_are_ranked_from_recorded_units(self):
        top = self.service.get_top_selling_products(
            2, CURRENT_START, CURRENT_END, "store-1"
        )
        low = self.service.get_low_performing_products(
            2, CURRENT_START, CURRENT_END, "store-1"
        )
        self.assertEqual(top[0]["product_name"], "Tea")
        self.assertEqual(top[0]["units_sold"], 5)
        self.assertEqual(low[0]["product_name"], "Biscuits")
        self.assertEqual(low[0]["units_sold"], 0)


class SalesAgentTests(unittest.TestCase):
    def test_comparison_returns_measured_product_trends_without_claiming_cause(self):
        agent = SalesIntelligenceAgent(example_database(), now=NOW)
        result = agent.run(
            SalesAgentRequest(
                question="Why did sales decrease compared with last week?",
                store_id="store-1",
            )
        )
        self.assertEqual(result["metrics"]["current_period_revenue"], 90)
        self.assertEqual(result["metrics"]["previous_period_revenue"], 120)
        self.assertEqual(result["metrics"]["revenue_change_percent"], -25)
        tea = next(row for row in result["insights"] if row["product_id"] == "p1")
        self.assertEqual(tea["trend"], "DECLINING")
        self.assertIn("10 to 5", tea["reason"])
        self.assertIn("not proof of why total revenue changed", result["summary"])

    def test_top_products_question_returns_product_level_sales(self):
        result = SalesIntelligenceAgent(example_database(), now=NOW).run(
            SalesAgentRequest(
                question="What were my best-selling products this week?",
                store_id="store-1",
            )
        )
        self.assertEqual(result["top_selling_products"][0]["product_name"], "Tea")
        self.assertEqual(result["top_selling_products"][0]["units_sold"], 5)

    def test_empty_period_returns_zero_metrics_and_warning(self):
        result = SalesIntelligenceAgent(FakeDatabase(), now=NOW).run(
            SalesAgentRequest(question="What is my revenue this month?")
        )
        self.assertEqual(result["metrics"]["current_period_revenue"], 0)
        self.assertTrue(any("No completed sales" in warning for warning in result["warnings"]))

    def test_forecast_uses_actual_history_baseline_and_marks_method(self):
        sales = [
            {
                "status": "completed",
                "store_id": "store-1",
                "created_at": datetime(2026, 10, day, tzinfo=timezone.utc),
                "items": [{"product_id": "p1", "name": "Tea", "quantity": 30}],
            }
            for day in (1, 4, 8)
        ]
        result = SalesIntelligenceAgent(
            FakeDatabase(sales), now=NOW
        ).run(
            SalesAgentRequest(
                question="Which products are likely to sell more next week?",
                product_id="p1",
            )
        )
        self.assertEqual(result["forecasts"][0]["predicted_units"], 7)
        self.assertEqual(result["forecasts"][0]["method"], "historical_average")


if __name__ == "__main__":
    unittest.main()
