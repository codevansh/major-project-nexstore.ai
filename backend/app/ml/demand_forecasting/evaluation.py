"""Chronological holdout, fixed-origin evaluation, and regression metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Sequence

from app.ml.demand_forecasting.data import DailyDemand
from app.ml.demand_forecasting.features import MIN_HISTORY_DAYS, TrainingExample, build_features


@dataclass(frozen=True)
class ChronologicalSplit:
    train_rows: list[TrainingExample]
    validation_rows: list[TrainingExample]
    validation_start: date
    validation_end: date


def make_chronological_split(
    examples: Sequence[TrainingExample], validation_days: int
) -> ChronologicalSplit:
    if validation_days < 1:
        raise ValueError("validation_days must be positive.")
    if not examples:
        raise ValueError("Cannot split an empty set of training examples.")
    end = max(row.target_date for row in examples)
    start = end - timedelta(days=validation_days - 1)
    return ChronologicalSplit(
        train_rows=[row for row in examples if row.target_date < start],
        validation_rows=[row for row in examples if row.target_date >= start],
        validation_start=start,
        validation_end=end,
    )


def regression_metrics(actual: list[float], predicted: list[float]) -> dict[str, float | None]:
    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    total = sum(actual)
    wape = sum(abs(a - p) for a, p in zip(actual, predicted)) / total if total > 0 else None
    return {"mae": mae, "rmse": rmse, "wape": wape}


def forecast_validation_window(
    daily_demand: tuple[DailyDemand, ...], estimator: Any | None,
    validation_start: date, validation_end: date,
) -> tuple[list[float], list[float]]:
    """Evaluate a fixed-origin horizon recursively, without holdout actuals as inputs."""
    from collections import defaultdict

    series: dict[str, list[DailyDemand]] = defaultdict(list)
    for point in daily_demand:
        series[point.product_id].append(point)
    actual_values: list[float] = []
    predictions: list[float] = []
    for product_id, points in series.items():
        points.sort(key=lambda point: point.demand_date)
        values = {point.demand_date: point.quantity for point in points}
        history = [point.quantity for point in points if point.demand_date < validation_start]
        if len(history) < MIN_HISTORY_DAYS:
            continue
        day = validation_start
        while day <= validation_end:
            actual = values.get(day)
            features = build_features(day, history, product_id=product_id)
            predicted = features["lag_7"] if estimator is None else float(estimator.predict([features])[0])
            predicted = max(0.0, float(predicted))
            if actual is not None:
                actual_values.append(actual)
                predictions.append(predicted)
            # Advance with the prediction, even if an observed calendar day is absent.
            history.append(predicted)
            day += timedelta(days=1)
    return actual_values, predictions
