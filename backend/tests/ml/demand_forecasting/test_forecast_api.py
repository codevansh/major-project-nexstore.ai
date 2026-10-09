import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.api.analytics import get_demand_forecast, router as analytics_router
from app.core.security import get_current_user
from app.schemas.demand_forecast import DemandForecastResponse
from app.services.demand_forecast_service import SyntheticDemoForecastService
from app.services.demand_forecast_service import SyntheticForecastUnavailableError
from app.ml.demand_forecasting.artifacts import load_model, persist_model
from app.ml.demand_forecasting.synthetic_data import (
    generate_synthetic_sales,
    synthetic_rows_to_sales_records,
    write_synthetic_sales_csv,
)
from app.ml.demand_forecasting.training import train_forecasting_model


class DemandForecastRouteIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_directory = tempfile.TemporaryDirectory()
        root = Path(cls.temp_directory.name)
        cls.artifact_path = root / "synthetic.joblib"
        cls.dataset_path = root / "synthetic.csv"
        rows = generate_synthetic_sales()
        write_synthetic_sales_csv(rows, cls.dataset_path)
        train_forecasting_model(
            synthetic_rows_to_sales_records(rows),
            random_state=42,
            n_estimators=10,
            artifact_path=cls.artifact_path,
            training_data_source="synthetic",
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_directory.cleanup()

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(analytics_router, prefix="/api")
        self.route = next(
            route
            for route in analytics_router.routes
            if getattr(route, "path", None) == "/analytics/demand-forecast"
        )

    def request_forecast(
        self,
        product_id="synthetic-product-01",
        *,
        horizon_days=7,
        artifact_path=None,
        dataset_path=None,
    ):
        service = SyntheticDemoForecastService(
            artifact_path or self.artifact_path,
            dataset_path or self.dataset_path,
        )
        return get_demand_forecast(
            product_id=product_id,
            horizon_days=horizon_days,
            service=service,
            _={},
        )

    def test_route_is_get_and_returns_explicit_synthetic_demo_response(self):
        self.assertIn("GET", self.route.methods)
        dependencies = {
            dependency.call for dependency in self.route.dependant.dependencies
        }
        self.assertIn(get_current_user, dependencies)
        self.assertIn(
            "/api/analytics/demand-forecast",
            self.app.openapi()["paths"],
        )
        result = self.request_forecast(horizon_days=5)
        response = DemandForecastResponse.model_validate(result)
        self.assertTrue(response.is_synthetic_demo)
        self.assertEqual(response.demo_label, "Synthetic demo forecast")
        self.assertEqual(response.data_source, "synthetic development CSV")
        self.assertEqual(response.horizon_days, 5)
        self.assertEqual(len(response.forecasts), 5)

    def test_unknown_product_maps_to_not_found(self):
        with self.assertRaises(HTTPException) as raised:
            self.request_forecast("not-a-synthetic-product")
        self.assertEqual(raised.exception.status_code, 404)

    def test_missing_artifact_and_dataset_map_to_service_unavailable(self):
        root = Path(self.temp_directory.name)
        empty_dataset = write_synthetic_sales_csv([], root / "empty.csv")
        corrupt_artifact = root / "corrupt.joblib"
        corrupt_artifact.write_text("not a joblib model", encoding="utf-8")
        for artifact, dataset in (
            (root / "missing.joblib", self.dataset_path),
            (corrupt_artifact, self.dataset_path),
            (self.artifact_path, root / "missing.csv"),
            (self.artifact_path, empty_dataset),
        ):
            with self.subTest(artifact=artifact.name, dataset=dataset.name):
                with self.assertRaises(HTTPException) as raised:
                    self.request_forecast(
                        artifact_path=artifact,
                        dataset_path=dataset,
                    )
                self.assertEqual(raised.exception.status_code, 503)

    def test_real_source_artifact_is_never_served_as_synthetic_demo(self):
        bundle = load_model(self.artifact_path)
        bundle["metadata"]["training_data_source"] = "mongodb"
        incompatible_artifact = Path(self.temp_directory.name) / "real-source.joblib"
        persist_model(bundle, incompatible_artifact)
        service = SyntheticDemoForecastService(incompatible_artifact, self.dataset_path)
        with self.assertRaises(SyntheticForecastUnavailableError):
            service.forecast("synthetic-product-01")

    def test_insufficient_product_history_and_stale_dataset_map_to_unprocessable(self):
        rows = generate_synthetic_sales()
        short_rows = [
            row
            for row in rows
            if row["product_id"] != "synthetic-product-01"
            or row["created_at"][:10] >= "2025-04-11"
        ]
        stale_rows = [
            row for row in rows if row["created_at"][:10] <= "2025-04-22"
        ]
        root = Path(self.temp_directory.name)
        for name, values, product_id in (
            ("short.csv", short_rows, "synthetic-product-01"),
            ("stale.csv", stale_rows, "synthetic-product-01"),
        ):
            path = write_synthetic_sales_csv(values, root / name)
            with self.subTest(dataset=name):
                with self.assertRaises(HTTPException) as raised:
                    self.request_forecast(
                        product_id,
                        dataset_path=path,
                    )
                self.assertEqual(raised.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
