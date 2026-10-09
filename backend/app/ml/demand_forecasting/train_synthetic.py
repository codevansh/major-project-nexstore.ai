"""Generate and evaluate synthetic data without connecting to MongoDB."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from app.ml.demand_forecasting.synthetic_data import (
    DEFAULT_DATASET_PATH,
    DEFAULT_DAYS,
    DEFAULT_PRODUCT_COUNT,
    DEFAULT_SEED,
    generate_synthetic_sales,
    load_synthetic_sales_records,
    write_synthetic_sales_csv,
)
from app.ml.demand_forecasting.training import (
    InsufficientTrainingDataError,
    train_forecasting_model,
)


DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "synthetic_demand_forecaster.joblib"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rewrite the canonical synthetic CSV from the fixed seed",
    )
    args = parser.parse_args()
    if DEFAULT_DATASET_PATH.exists() and not args.regenerate:
        dataset_path = DEFAULT_DATASET_PATH
    else:
        rows = generate_synthetic_sales(
            days=DEFAULT_DAYS,
            product_count=DEFAULT_PRODUCT_COUNT,
            seed=DEFAULT_SEED,
        )
        dataset_path = write_synthetic_sales_csv(rows, DEFAULT_DATASET_PATH)
    records = load_synthetic_sales_records(dataset_path)
    try:
        bundle, report = train_forecasting_model(
            records,
            random_state=DEFAULT_SEED,
            artifact_path=DEFAULT_ARTIFACT,
            training_data_source="synthetic",
        )
    except InsufficientTrainingDataError as exc:
        print(f"Synthetic training stopped: {exc}; no model artifact was written.")
        return 3

    quality = asdict(report["quality"])
    print("Training source: SYNTHETIC development data; not real-world evaluation.")
    print(f"Synthetic CSV rows / sales documents: {quality['total_transactions']}")
    print(f"Synthetic products: {DEFAULT_PRODUCT_COUNT}")
    print(f"Synthetic history days: {DEFAULT_DAYS}")
    print(f"Fixed random seed: {DEFAULT_SEED}")
    print(f"Training rows: {report['training_rows']}")
    print(f"Validation rows: {report['validation_rows']}")
    print(f"Validation window: {report['validation_start']} to {report['validation_end']}")
    print(f"Seasonal-naive metrics (MAE/RMSE/WAPE): {report['baseline_metrics']}")
    print(f"Random Forest metrics (MAE/RMSE/WAPE): {report['random_forest_metrics']}")
    print(f"HistGradientBoosting metrics (MAE/RMSE/WAPE): {report['hist_gradient_boosting_metrics']}")
    print(f"Candidate results: {report['candidate_results']}")
    print(f"Selected model: {bundle['selected_model']}")
    print(f"Synthetic dataset saved: {dataset_path}")
    print(f"Synthetic model artifact saved: {DEFAULT_ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
