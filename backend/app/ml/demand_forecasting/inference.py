"""Inference for product-level daily demand forecasts."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
from typing import Any, Iterable

from app.ml.demand_forecasting.data import parse_daily_date, prepare_sales_data
from app.ml.demand_forecasting.features import (
    FEATURE_VERSION,
    MIN_HISTORY_DAYS,
    build_features,
)
from app.ml.demand_forecasting.artifacts import load_model


class InsufficientHistoryError(ValueError):
    """Raised when observed sales do not support a reliable forecast."""


def _forecast_origin(value: date | datetime | str) -> date:
    parsed = parse_daily_date(value)
    if parsed is None:
        raise ValueError("forecast_origin must be a valid date, datetime, or ISO date string.")
    return parsed


def predict_product_demand(
    model_bundle: dict[str, Any],
    sales_records: Iterable[dict[str, Any]],
    product_id: str,
    forecast_origin: date | datetime | str,
    *,
    horizon_days: int = 7,
) -> dict[str, Any]:
    """Forecast daily product quantity for dates after the end-of-day origin.

    ``sales_records`` may include later transactions; preprocessing excludes
    transactions after the forecast origin before creating any features.
    Predictions are recursive, so later horizon features use earlier
    predictions rather than future observed demand.
    """
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("product_id must be a nonempty string.")
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int):
        raise ValueError("horizon_days must be an integer from 1 to 30.")
    if not 1 <= horizon_days <= 30:
        raise ValueError("horizon_days must be an integer from 1 to 30.")
    origin = _forecast_origin(forecast_origin)
    if model_bundle.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Model feature version is unsupported.")
    trained_through = parse_daily_date(model_bundle.get("trained_through"))
    if trained_through is None:
        raise ValueError("Model artifact is missing a valid training cutoff.")
    if origin < trained_through:
        raise ValueError("forecast_origin cannot precede the model training cutoff.")

    prepared = prepare_sales_data(sales_records, through_date=origin)
    observed_through = prepared.quality.observed_through
    if observed_through is None or (origin - observed_through).days > 7:
        raise InsufficientHistoryError(
            "Sales history does not cover the forecast origin (maximum allowed gap: 7 days)."
        )
    history = [
        point.quantity
        for point in prepared.daily_demand
        if point.product_id == product_id and point.demand_date <= origin
    ]
    if len(history) < MIN_HISTORY_DAYS:
        raise InsufficientHistoryError(
            f"Product {product_id!r} needs at least {MIN_HISTORY_DAYS} daily history values."
        )

    selected_model = model_bundle.get("selected_model")
    estimator = model_bundle.get("estimator")
    predictions = []
    for offset in range(1, horizon_days + 1):
        target_date = origin + timedelta(days=offset)
        features = build_features(
            target_date,
            history,
            product_id=product_id,
            series_age_days=len(history),
        )
        if selected_model == "seasonal_naive_7":
            predicted = features["lag_7"]
        elif selected_model == "random_forest" and estimator is not None:
            predicted = float(estimator.predict([features])[0])
        elif selected_model == "hist_gradient_boosting" and estimator is not None:
            predicted = float(estimator.predict([features])[0])
        else:
            raise ValueError("Model artifact has an unsupported selected model.")
        predicted_quantity = float(predicted)
        # Demand policy: negative or non-finite estimator outputs become zero.
        quantity = max(0.0, predicted_quantity) if math.isfinite(predicted_quantity) else 0.0
        predictions.append(
            {"date": target_date.isoformat(), "predicted_quantity": quantity}
        )
        history.append(quantity)

    return {
        "product_id": product_id,
        "forecast_origin": origin.isoformat(),
        "horizon_days": horizon_days,
        "unit": "items per day across all stores",
        "model": selected_model,
        "forecasts": predictions,
    }


class DemandForecastService:
    """Database-backed inference adapter; no API route is registered."""

    def __init__(self, db: Any, artifact_path: str | Path):
        self.db = db
        self.artifact_path = Path(artifact_path)

    def forecast(
        self,
        product_id: str,
        forecast_origin: date | datetime | str,
        *,
        horizon_days: int = 7,
    ) -> dict[str, Any]:
        origin = _forecast_origin(forecast_origin)
        from app.ml.demand_forecasting.repository import load_sales_history

        bundle = load_model(self.artifact_path)
        records = load_sales_history(self.db, through_date=origin)
        return predict_product_demand(
            bundle,
            records,
            product_id,
            origin,
            horizon_days=horizon_days,
        )
