import csv
import tempfile
import unittest
import importlib.util
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.ml.demand_forecasting.data import DailyDemand, prepare_sales_data
from app.ml.demand_forecasting.artifacts import load_model
from app.ml.demand_forecasting.evaluation import regression_metrics
from app.ml.demand_forecasting.features import make_training_examples
from app.ml.demand_forecasting.inference import (
    DemandForecastService,
    InsufficientHistoryError,
    predict_product_demand,
)
from app.ml.demand_forecasting.repository import load_sales_history
from app.ml.demand_forecasting.synthetic_data import (
    CSV_COLUMNS,
    generate_synthetic_sales,
    load_synthetic_sales_records,
    synthetic_rows_to_sales_records,
    write_synthetic_sales_csv,
)
from app.ml.demand_forecasting.training import (
    InsufficientTrainingDataError,
    train_forecasting_model,
)


def synthetic_sales(days=100):
    """Clearly synthetic, deterministic fixture; never represents store data."""
    start = date(2024, 1, 1)
    records = []
    for product_id, base in (("synthetic-a", 8), ("synthetic-b", 3)):
        for offset in range(days):
            day = start + timedelta(days=offset)
            quantity = base + (day.weekday() in (4, 5)) * 4 + offset // 30
            records.append(
                {
                    "status": "completed",
                    "created_at": datetime.combine(
                        day, datetime.min.time(), tzinfo=timezone.utc
                    ),
                    "items": [{"product_id": product_id, "quantity": quantity}],
                }
            )
    return records


class SalesPreparationTests(unittest.TestCase):
    def test_filters_status_and_counts_bad_timestamps_and_lines(self):
        records = [
            {
                "status": "completed",
                "created_at": "2025-01-01T11:00:00Z",
                "items": [
                    {"product_id": "p1", "quantity": 2},
                    {"product_id": "", "quantity": 2},
                    {"product_id": "p1", "quantity": 0},
                ],
            },
            {"status": "cancelled", "created_at": "bad", "items": []},
            {"status": "completed", "created_at": "bad", "items": []},
        ]
        result = prepare_sales_data(records)
        self.assertEqual(len(result.daily_demand), 1)
        self.assertEqual(result.daily_demand[0].quantity, 2)
        self.assertEqual(result.quality.completed_transactions, 2)
        self.assertEqual(result.quality.excluded_non_completed_transactions, 1)
        self.assertEqual(result.quality.invalid_timestamps, 1)
        self.assertEqual(result.quality.missing_product_id_lines, 1)
        self.assertEqual(result.quality.invalid_quantity_lines, 1)

    def test_fills_missing_days_with_zero_for_each_product(self):
        result = prepare_sales_data(
            [
                {
                    "status": "completed",
                    "created_at": "2025-01-01",
                    "items": [{"product_id": "p", "quantity": 1}],
                },
                {
                    "status": "completed",
                    "created_at": "2025-01-03",
                    "items": [{"product_id": "p", "quantity": 3}],
                },
            ]
        )
        self.assertEqual([row.quantity for row in result.daily_demand], [1, 0, 3])

    def test_does_not_extend_product_to_another_products_last_sale(self):
        result = prepare_sales_data(
            [
                {
                    "status": "completed",
                    "created_at": "2025-01-01",
                    "items": [{"product_id": "p1", "quantity": 1}],
                },
                {
                    "status": "completed",
                    "created_at": "2025-01-03",
                    "items": [{"product_id": "p2", "quantity": 1}],
                },
            ]
        )
        p1_days = [row.demand_date.isoformat() for row in result.daily_demand if row.product_id == "p1"]
        self.assertEqual(p1_days, ["2025-01-01"])


class FeatureLeakageTests(unittest.TestCase):
    def test_training_features_only_use_previous_days(self):
        start = date(2025, 1, 1)
        series = [
            DailyDemand("p", start + timedelta(days=i), float(i + 1)) for i in range(40)
        ]
        original = make_training_examples(series)
        changed_future = list(series)
        changed_future[-1] = DailyDemand("p", changed_future[-1].demand_date, 99999.0)
        changed = make_training_examples(changed_future)
        self.assertEqual(original[-1].features, changed[-1].features)
        self.assertNotEqual(original[-1].target, changed[-1].target)
        self.assertEqual(original[0].features["lag_1"], 28.0)

    def test_lags_rolling_features_and_target_are_date_aligned(self):
        start = date(2025, 1, 1)
        series = [
            DailyDemand("p", start + timedelta(days=i), float(i + 1))
            for i in range(35)
        ]
        examples = make_training_examples(series)
        first = examples[0]
        self.assertEqual(first.target_date, start + timedelta(days=28))
        self.assertEqual(first.target, 29.0)
        self.assertEqual(first.features["lag_1"], 28.0)
        self.assertEqual(first.features["lag_7"], 22.0)
        self.assertEqual(first.features["lag_14"], 15.0)
        self.assertEqual(first.features["lag_28"], 1.0)
        self.assertEqual(first.features["rolling_mean_7"], 25.0)
        self.assertEqual(first.features["rolling_mean_28"], 14.5)
        self.assertNotIn("target", first.features)
        self.assertNotIn("quantity", first.features)


class ExtractionTests(unittest.TestCase):
    def test_extraction_projects_forecast_fields_and_can_limit_date(self):
        from unittest.mock import Mock

        db = Mock()
        db.sales.find.return_value = []
        load_sales_history(db, through_date=date(2025, 1, 2))
        query, projection = db.sales.find.call_args.args
        self.assertEqual(
            query["created_at"]["$lt"],
            datetime(2025, 1, 3, tzinfo=timezone.utc),
        )
        self.assertEqual(projection["items.product_id"], 1)
        self.assertEqual(projection["items.quantity"], 1)
        self.assertNotIn("customer_id", projection)


@unittest.skipUnless(
    importlib.util.find_spec("sklearn") and importlib.util.find_spec("joblib"),
    "install backend requirements to run scikit-learn training tests",
)
class TrainingAndInferenceTests(unittest.TestCase):
    def test_chronological_evaluation_and_joblib_persistence(self):
        records = synthetic_sales()
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "demand.joblib"
            bundle, report = train_forecasting_model(
                records,
                validation_days=7,
                n_estimators=20,
                artifact_path=artifact,
            )
            self.assertTrue(artifact.is_file())
            self.assertEqual(report["validation_start"], "2024-04-03")
            self.assertEqual(report["validation_end"], "2024-04-09")
            self.assertGreater(report["training_rows"], 0)
            self.assertGreater(report["validation_rows"], 0)
            self.assertIn("mae", report["baseline_metrics"])
            self.assertIn("rmse", report["random_forest_metrics"])
            self.assertIn("wape", report["random_forest_metrics"])
            self.assertIn("hist_gradient_boosting", report["candidate_results"])
            self.assertIn("training_data_source", bundle["metadata"])
            self.assertEqual(
                load_model(artifact)["selected_model"], bundle["selected_model"]
            )

    def test_inference_uses_only_data_through_origin_and_returns_daily_quantities(self):
        records = synthetic_sales()
        bundle, _ = train_forecasting_model(records, n_estimators=10)
        origin = date(2024, 4, 9)
        result = predict_product_demand(
            bundle, records, "synthetic-a", origin, horizon_days=7
        )
        with_future = records + [
            {
                "status": "completed",
                "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
                "items": [{"product_id": "synthetic-a", "quantity": 99999}],
            }
        ]
        same_result = predict_product_demand(
            bundle, with_future, "synthetic-a", origin, horizon_days=7
        )
        self.assertEqual(result, same_result)
        self.assertEqual(result["unit"], "items per day across all stores")
        self.assertEqual(len(result["forecasts"]), 7)
        self.assertTrue(
            all(row["predicted_quantity"] >= 0 for row in result["forecasts"])
        )


class ValidationTests(unittest.TestCase):
    def test_training_and_inference_reject_insufficient_inputs(self):
        with self.assertRaises(InsufficientTrainingDataError):
            train_forecasting_model(synthetic_sales(days=30), n_estimators=5)
        sales = synthetic_sales(days=20)
        bundle = {
            "feature_version": "daily-demand-v1",
            "selected_model": "seasonal_naive_7",
            "trained_through": "2024-01-20",
            "estimator": None,
        }
        with self.assertRaises(InsufficientHistoryError):
            predict_product_demand(bundle, sales, "synthetic-a", "2024-01-20")
        with self.assertRaises(ValueError):
            predict_product_demand(
                bundle, sales, "synthetic-a", "2024-01-20", horizon_days=0
            )
        with self.assertRaises(ValueError):
            predict_product_demand(
                bundle, sales, "synthetic-a", "2024-01-20", horizon_days=1.5
            )


class SyntheticDatasetTests(unittest.TestCase):
    def test_generation_is_reproducible_for_a_fixed_seed(self):
        first = generate_synthetic_sales()
        second = generate_synthetic_sales()
        self.assertEqual(first, second)

    def test_generated_csv_has_expected_schema_and_row_count(self):
        rows = generate_synthetic_sales()
        with tempfile.TemporaryDirectory() as directory:
            path = write_synthetic_sales_csv(
                rows, Path(directory) / "synthetic_sales.csv"
            )
            with path.open("r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                self.assertEqual(tuple(reader.fieldnames or ()), CSV_COLUMNS)
                stored_rows = list(reader)
        self.assertEqual(len(stored_rows), 120 * 10)
        self.assertEqual(len({row["product_id"] for row in stored_rows}), 10)
        self.assertEqual(
            len({row["created_at"][:10] for row in stored_rows}), 120
        )
        self.assertTrue(all(row["status"] == "completed" for row in stored_rows))
        self.assertTrue(
            all(int(row["quantity"]) > 0 for row in stored_rows)
        )

    def test_csv_rows_convert_to_expected_in_memory_sales_structure(self):
        rows = generate_synthetic_sales()
        expected_records = synthetic_rows_to_sales_records(rows)
        with tempfile.TemporaryDirectory() as directory:
            path = write_synthetic_sales_csv(
                rows, Path(directory) / "synthetic_sales.csv"
            )
            records = load_synthetic_sales_records(path)

        self.assertEqual(records, expected_records)
        self.assertEqual(len(records), 120 * 10)
        self.assertEqual(
            set(records[0]), {"created_at", "status", "items"}
        )
        self.assertEqual(
            set(records[0]["items"][0]), {"product_id", "quantity"}
        )
        self.assertIsInstance(records[0]["items"][0]["quantity"], int)

    def test_generated_history_meets_existing_feature_history_requirement(self):
        records = synthetic_rows_to_sales_records(generate_synthetic_sales())
        prepared = prepare_sales_data(records)
        self.assertEqual(len(prepared.daily_demand), 120 * 10)
        examples = make_training_examples(prepared.daily_demand)
        self.assertEqual(len(examples), (120 - 28) * 10)

    def test_generated_sales_train_and_evaluate_with_existing_pipeline(self):
        bundle, report = train_forecasting_model(
            synthetic_rows_to_sales_records(generate_synthetic_sales()),
            random_state=42,
            n_estimators=20,
        )
        self.assertGreater(report["training_rows"], 0)
        self.assertGreater(report["validation_rows"], 0)
        self.assertIn(bundle["selected_model"], {"seasonal_naive_7", "random_forest", "hist_gradient_boosting"})
        self.assertIn("mae", report["baseline_metrics"])
        self.assertIn("rmse", report["random_forest_metrics"])
        self.assertIn("wape", report["hist_gradient_boosting_metrics"])
        self.assertEqual(bundle["metadata"]["training_data_source"], "unknown")
        self.assertEqual(bundle["metadata"]["forecast_frequency"], "daily")

    def test_candidate_failures_are_reported_without_silent_exclusion(self):
        from unittest.mock import patch
        from app.ml.demand_forecasting.candidates import make_model_candidates

        candidates = make_model_candidates(42, 5)
        class FailedEstimator:
            def fit(self, *_args, **_kwargs):
                raise RuntimeError("deliberate candidate failure")
        candidates["hist_gradient_boosting"] = FailedEstimator()
        with patch("app.ml.demand_forecasting.training.make_model_candidates", return_value=candidates):
            _, report = train_forecasting_model(
                synthetic_rows_to_sales_records(generate_synthetic_sales()), n_estimators=5
            )
        failure = report["candidate_results"]["hist_gradient_boosting"]
        self.assertEqual(failure["status"], "failed")
        self.assertEqual(failure["error_type"], "RuntimeError")
        self.assertEqual(failure["error"], "deliberate candidate failure")

    def test_metrics_and_nonfinite_forecast_policy(self):
        self.assertEqual(regression_metrics([1.0, 3.0], [2.0, 1.0]), {
            "mae": 1.5,
            "rmse": math.sqrt(2.5),
            "wape": 0.75,
        })
        class NonfiniteEstimator:
            def predict(self, _rows):
                return [float("nan")]
        bundle = {
            "feature_version": "daily-demand-v1",
            "selected_model": "random_forest",
            "estimator": NonfiniteEstimator(),
            "trained_through": "2024-04-09",
        }
        result = predict_product_demand(bundle, synthetic_sales(), "synthetic-a", "2024-04-09", horizon_days=1)
        self.assertEqual(result["forecasts"][0]["predicted_quantity"], 0.0)


@unittest.skipUnless(
    importlib.util.find_spec("sklearn") and importlib.util.find_spec("joblib"),
    "install backend requirements to run scikit-learn inference tests",
)
class SyntheticArtifactInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = generate_synthetic_sales()
        cls.records = synthetic_rows_to_sales_records(cls.rows)
        cls.temp_directory = tempfile.TemporaryDirectory()
        cls.artifact_path = Path(cls.temp_directory.name) / "synthetic-demand.joblib"
        train_forecasting_model(
            cls.records,
            random_state=42,
            n_estimators=20,
            artifact_path=cls.artifact_path,
        )
        cls.model_bundle = load_model(cls.artifact_path)

    @classmethod
    def tearDownClass(cls):
        cls.temp_directory.cleanup()

    def test_saved_artifact_forecasts_multiple_products_with_valid_output(self):
        origin = date(2025, 4, 30)
        products = ["synthetic-product-01", "synthetic-product-10"]
        expected_dates = [
            (origin + timedelta(days=offset)).isoformat()
            for offset in range(1, 8)
        ]
        for product_id in products:
            with self.subTest(product_id=product_id):
                result = predict_product_demand(
                    self.model_bundle,
                    self.records,
                    product_id,
                    origin,
                    horizon_days=7,
                )
                self.assertEqual(
                    set(result),
                    {
                        "product_id",
                        "forecast_origin",
                        "horizon_days",
                        "unit",
                        "model",
                        "forecasts",
                    },
                )
                self.assertEqual(result["product_id"], product_id)
                self.assertEqual(result["forecast_origin"], origin.isoformat())
                self.assertEqual(result["horizon_days"], 7)
                self.assertEqual(len(result["forecasts"]), 7)
                self.assertEqual(
                    [forecast["date"] for forecast in result["forecasts"]],
                    expected_dates,
                )
                for forecast in result["forecasts"]:
                    self.assertEqual(
                        set(forecast), {"date", "predicted_quantity"}
                    )
                    self.assertTrue(math.isfinite(forecast["predicted_quantity"]))
                    self.assertGreaterEqual(forecast["predicted_quantity"], 0)

    def test_records_after_forecast_origin_do_not_change_predictions(self):
        future_sale = {
            "status": "completed",
            "created_at": "2025-05-01T12:00:00+00:00",
            "items": [
                {"product_id": "synthetic-product-01", "quantity": 1_000_000}
            ],
        }
        original = predict_product_demand(
            self.model_bundle,
            self.records,
            "synthetic-product-01",
            "2025-04-30",
        )
        with_future = predict_product_demand(
            self.model_bundle,
            self.records + [future_sale],
            "synthetic-product-01",
            "2025-04-30",
        )
        self.assertEqual(original, with_future)

    def test_insufficient_history_and_unknown_product_are_rejected(self):
        origin = date(2025, 4, 30)
        short_history = [
            record
            for record in self.records
            if record["items"][0]["product_id"] != "synthetic-product-01"
            or record["created_at"] >= "2025-04-11"
        ]
        with self.assertRaisesRegex(InsufficientHistoryError, "at least 28 daily"):
            predict_product_demand(
                self.model_bundle,
                short_history,
                "synthetic-product-01",
                origin,
            )
        with self.assertRaisesRegex(InsufficientHistoryError, "needs at least 28"):
            predict_product_demand(
                self.model_bundle,
                self.records,
                "synthetic-product-unknown",
                origin,
            )

    def test_stale_history_and_origin_before_training_cutoff_are_rejected(self):
        stale_records = [
            record for record in self.records if record["created_at"] <= "2025-04-22"
        ]
        with self.assertRaisesRegex(InsufficientHistoryError, "maximum allowed gap: 7 days"):
            predict_product_demand(
                self.model_bundle,
                stale_records,
                "synthetic-product-01",
                "2025-05-01",
            )
        with self.assertRaisesRegex(ValueError, "cannot precede the model training cutoff"):
            predict_product_demand(
                self.model_bundle,
                self.records,
                "synthetic-product-01",
                "2025-04-29",
            )

    def test_database_adapter_uses_synthetic_mock_records_only(self):
        from unittest.mock import Mock

        db = Mock()
        db.sales.find.return_value = self.records
        service = DemandForecastService(db, self.artifact_path)
        result = service.forecast(
            "synthetic-product-01", "2025-04-30", horizon_days=3
        )
        self.assertEqual(len(result["forecasts"]), 3)
        query, _ = db.sales.find.call_args.args
        self.assertEqual(
            query["created_at"]["$lt"],
            datetime(2025, 5, 1, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
