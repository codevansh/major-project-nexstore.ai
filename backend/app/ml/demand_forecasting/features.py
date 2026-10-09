"""Causal calendar, lag, and rolling features for daily demand."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import math
from typing import Iterable

from app.ml.demand_forecasting.data import DailyDemand


FEATURE_VERSION = "daily-demand-v1"
MIN_HISTORY_DAYS = 28


@dataclass(frozen=True)
class TrainingExample:
    product_id: str
    target_date: date
    features: dict[str, float]
    target: float


def build_features(
    target_date: date,
    history: list[float],
    *,
    product_id: str | None = None,
    series_age_days: int | None = None,
) -> dict[str, float]:
    """Build target-day features from observations strictly before that day."""
    if len(history) < MIN_HISTORY_DAYS:
        raise ValueError(f"At least {MIN_HISTORY_DAYS} prior daily values are required.")
    prior = history[-MIN_HISTORY_DAYS:]
    day_of_year = target_date.timetuple().tm_yday
    features = {
        f"weekday_{target_date.weekday()}": 1.0,
        "month_sin": math.sin(2 * math.pi * target_date.month / 12),
        "month_cos": math.cos(2 * math.pi * target_date.month / 12),
        "year_day_sin": math.sin(2 * math.pi * day_of_year / 365.25),
        "year_day_cos": math.cos(2 * math.pi * day_of_year / 365.25),
        "series_age_days": float(series_age_days if series_age_days is not None else len(history)),
        "lag_1": float(prior[-1]),
        "lag_7": float(prior[-7]),
        "lag_14": float(prior[-14]),
        "lag_28": float(prior[-28]),
        "rolling_mean_7": sum(prior[-7:]) / 7,
        "rolling_mean_28": sum(prior) / 28,
    }
    if product_id:
        features[f"product_{product_id}"] = 1.0
    return features


def make_training_examples(
    daily_demand: Iterable[DailyDemand],
    *,
    min_history_days: int = MIN_HISTORY_DAYS,
) -> list[TrainingExample]:
    """Create one-step-ahead examples; every feature uses earlier dates only."""
    if min_history_days < MIN_HISTORY_DAYS:
        raise ValueError(f"min_history_days cannot be less than {MIN_HISTORY_DAYS}.")
    grouped: dict[str, list[DailyDemand]] = defaultdict(list)
    for point in daily_demand:
        grouped[point.product_id].append(point)

    examples: list[TrainingExample] = []
    for product_id, points in sorted(grouped.items()):
        points.sort(key=lambda point: point.demand_date)
        history: list[float] = []
        for index, point in enumerate(points):
            if len(history) >= min_history_days:
                examples.append(
                    TrainingExample(
                        product_id=product_id,
                        target_date=point.demand_date,
                        features=build_features(
                            point.demand_date,
                            history,
                            product_id=product_id,
                            series_age_days=index,
                        ),
                        target=point.quantity,
                    )
                )
            history.append(point.quantity)
    return examples
