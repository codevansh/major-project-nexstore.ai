"""Run ``python -m app.ml.demand_forecasting.train`` from backend/."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

from app.ml.demand_forecasting.repository import load_sales_history
from app.ml.demand_forecasting.training import (
    InsufficientTrainingDataError,
    train_forecasting_model,
)

DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[1] / "artifacts" / "demand_forecaster.joblib"
)


def main() -> int:
    try:
        from app.core.database import get_database, test_database_connection

        if not test_database_connection():
            print(
                "Training stopped: configured MongoDB is unavailable; no model was trained."
            )
            return 2
        records = load_sales_history(get_database())
    except Exception:
        # Do not echo driver exceptions; they can contain connection details.
        print(
            "Training stopped: database configuration or extraction failed; details withheld."
        )
        return 2

    try:
        bundle, report = train_forecasting_model(
            records, artifact_path=DEFAULT_ARTIFACT, training_data_source="mongodb"
        )
    except InsufficientTrainingDataError as exc:
        print(f"Training stopped: {exc}; no model artifact was written.")
        return 3

    quality = asdict(report["quality"])
    print("Training source: configured MongoDB sales data (real data).")
    print(f"Completed transactions: {quality['completed_transactions']}")
    print(f"Eligible transactions: {quality['eligible_transactions']}")
    print(f"Invalid timestamps: {quality['invalid_timestamps']}")
    print(f"Missing product IDs: {quality['missing_product_id_lines']}")
    print(f"Invalid quantities: {quality['invalid_quantity_lines']}")
    print(f"Selected model: {bundle['selected_model']}")
    print(
        f"Training rows: {report['training_rows']}; validation rows: {report['validation_rows']}"
    )
    print(f"Baseline metrics (MAE/RMSE/WAPE): {report['baseline_metrics']}")
    print(f"Random forest metrics (MAE/RMSE/WAPE): {report['random_forest_metrics']}")
    print(f"HistGradientBoosting metrics (MAE/RMSE/WAPE): {report['hist_gradient_boosting_metrics']}")
    print(f"Candidate results: {report['candidate_results']}")
    print(f"Artifact written: {DEFAULT_ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
