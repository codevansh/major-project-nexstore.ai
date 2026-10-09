"""Shared orchestration for chronological demand model comparison."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.ml.demand_forecasting.artifacts import persist_model
from app.ml.demand_forecasting.candidates import make_model_candidates
from app.ml.demand_forecasting.data import prepare_sales_data
from app.ml.demand_forecasting.evaluation import (
    forecast_validation_window,
    make_chronological_split,
    regression_metrics,
)
from app.ml.demand_forecasting.features import (
    FEATURE_VERSION,
    MIN_HISTORY_DAYS,
    make_training_examples,
)


class InsufficientTrainingDataError(ValueError):
    """Raised when chronological training and evaluation sets are too small."""


def train_forecasting_model(
    sales_records: Iterable[dict[str, Any]],
    *,
    validation_days: int = 7,
    min_training_rows: int = 30,
    n_estimators: int = 100,
    random_state: int = 42,
    artifact_path: str | Path | None = None,
    training_data_source: str = "unknown",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compare seasonal-naive, RF, and HGB using one chronological holdout.

    Validation forecasts use a fixed origin and recursively consume predictions.
    Failed estimators remain visible in the report and are never silently omitted.
    Selection uses lowest validation MAE, with deterministic tie priority:
    seasonal-naive, Random Forest, then HistGradientBoosting.
    """
    if validation_days < 1:
        raise ValueError("validation_days must be positive.")
    if min_training_rows < 1 or n_estimators < 1:
        raise ValueError("Training row and estimator counts must be positive.")
    prepared = prepare_sales_data(sales_records)
    examples = make_training_examples(prepared.daily_demand)
    if not examples:
        raise InsufficientTrainingDataError(
            f"At least {MIN_HISTORY_DAYS + 1} daily observations per product are required."
        )
    split = make_chronological_split(examples, validation_days)
    train_rows, validation_rows = split.train_rows, split.validation_rows
    if len(train_rows) < min_training_rows or not validation_rows:
        raise InsufficientTrainingDataError(
            "Insufficient chronological history for the requested training and validation split."
        )

    actual, baseline_predictions = forecast_validation_window(
        prepared.daily_demand, None, split.validation_start, split.validation_end
    )
    if not actual:
        raise InsufficientTrainingDataError(
            "No product has enough pre-validation history for chronological evaluation."
        )
    baseline_metrics = regression_metrics(actual, baseline_predictions)
    candidate_results: dict[str, dict[str, Any]] = {
        "seasonal_naive_7": {"status": "evaluated", "metrics": baseline_metrics}
    }
    candidate_metrics: dict[str, dict[str, float | None]] = {}
    candidates = make_model_candidates(random_state, n_estimators)
    for name, estimator in candidates.items():
        try:
            estimator.fit([row.features for row in train_rows], [row.target for row in train_rows])
            candidate_actual, predictions = forecast_validation_window(
                prepared.daily_demand, estimator, split.validation_start, split.validation_end
            )
            if candidate_actual != actual:
                raise RuntimeError("Candidate evaluation did not align with baseline targets.")
            metrics = regression_metrics(actual, predictions)
            candidate_metrics[name] = metrics
            candidate_results[name] = {"status": "evaluated", "metrics": metrics}
        except Exception as exc:
            candidate_results[name] = {
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    priority = {"seasonal_naive_7": 0, "random_forest": 1, "hist_gradient_boosting": 2}
    evaluated = [name for name, result in candidate_results.items() if result["status"] == "evaluated"]
    selected_model = min(evaluated, key=lambda name: (candidate_results[name]["metrics"]["mae"], priority[name]))
    selected_estimator = None
    if selected_model != "seasonal_naive_7":
        selected_estimator = candidates[selected_model]
        selected_estimator.fit([row.features for row in examples], [row.target for row in examples])

    trained_through = max(point.demand_date for point in prepared.daily_demand).isoformat()
    metadata = {
        "model_type": selected_model,
        "training_data_source": training_data_source,
        "training_timestamp": datetime.now(timezone.utc).isoformat(),
        "target": "daily product quantity across stores",
        "forecast_frequency": "daily",
        "feature_schema_version": FEATURE_VERSION,
        "validation_days": validation_days,
        "validation_start": split.validation_start.isoformat(),
        "validation_end": split.validation_end.isoformat(),
        "training_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "candidate_results": candidate_results,
    }
    bundle: dict[str, Any] = {
        "artifact_version": 2,
        "feature_version": FEATURE_VERSION,
        "selected_model": selected_model,
        "estimator": selected_estimator,
        "trained_through": trained_through,
        "trained_at": metadata["training_timestamp"],
        "metadata": metadata,
    }
    report = {
        "selected_model": selected_model,
        "training_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "validation_start": split.validation_start.isoformat(),
        "validation_end": split.validation_end.isoformat(),
        "candidate_results": candidate_results,
        "baseline_metrics": baseline_metrics,
        "random_forest_metrics": candidate_metrics.get("random_forest"),
        "hist_gradient_boosting_metrics": candidate_metrics.get("hist_gradient_boosting"),
        "quality": prepared.quality,
    }
    if artifact_path is not None:
        persist_model(bundle, artifact_path)
    return bundle, report
