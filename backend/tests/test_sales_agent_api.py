import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agents import router
from app.core.database import get_database
from tests.test_sales_agent import example_database


class SalesAgentApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api")
        db = example_database()
        app.dependency_overrides[get_database] = lambda: db
        self.client = TestClient(app)

    def test_sales_agent_api_returns_structured_comparison(self):
        response = self.client.post(
            "/api/agents/sales",
            json={
                "question": "Why did sales decrease compared with last week?",
                "analysis": "comparison",
                "store_id": "store-1",
                "start_date": "2026-10-03T00:00:00+00:00",
                "end_date": "2026-10-10T00:00:00+00:00",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["agent"], "Sales Intelligence Agent")
        self.assertEqual(payload["metrics"]["current_period_revenue"], 90)
        self.assertEqual(payload["metrics"]["revenue_change_percent"], -25)
        self.assertIsInstance(payload["insights"], list)

    def test_invalid_date_range_is_rejected(self):
        response = self.client.post(
            "/api/agents/sales",
            json={
                "question": "Show sales",
                "start_date": "2026-10-10T00:00:00+00:00",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
