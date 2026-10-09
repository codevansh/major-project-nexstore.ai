"""Application service for clearly labeled synthetic demo forecasts."""

from pathlib import Path
from typing import Any

from app.ml.demand_forecasting.data import parse_daily_date
from app.ml.demand_forecasting.features import FEATURE_VERSION
from app.ml.demand_forecasting.inference import (
    InsufficientHistoryError,
    predict_product_demand,
)
from app.ml.demand_forecasting.synthetic_data import (
    DEFAULT_DATASET_PATH,
    load_synthetic_sales_records,
)
from app.ml.demand_forecasting.artifacts import load_model

DEFAULT_SYNTHETIC_ARTIFACT = (
    Path(__file__).resolve().parents[1]
    / "ml"
    / "artifacts"
    / "synthetic_demand_forecaster.joblib"
)


class SyntheticForecastUnavailableError(RuntimeError):
    """Raised when synthetic demo inputs or the saved model are unavailable."""


class SyntheticProductNotFoundError(LookupError):
    """Raised when a product is not part of the synthetic demo dataset."""


class SyntheticDemoForecastService:
    def __init__(
        self,
        artifact_path: str | Path = DEFAULT_SYNTHETIC_ARTIFACT,
        dataset_path: str | Path = DEFAULT_DATASET_PATH,
    ):
        self.artifact_path = Path(artifact_path)
        self.dataset_path = Path(dataset_path)

    def forecast(self, product_id: str, *, horizon_days: int = 7) -> dict[str, Any]:
        try:
            bundle = load_model(self.artifact_path)
        except Exception as exc:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo model artifact is unavailable or invalid."
            ) from exc
        if bundle.get("feature_version") != FEATURE_VERSION:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo model uses an unsupported feature version."
            )
        if bundle.get("metadata", {}).get("training_data_source") != "synthetic":
            raise SyntheticForecastUnavailableError(
                "The demo endpoint requires an artifact trained from synthetic development data."
            )

        try:
            records = load_synthetic_sales_records(self.dataset_path)
        except Exception as exc:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo sales dataset is unavailable or invalid."
            ) from exc
        if not records:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo sales dataset contains no records."
            )

        available_products = {
            item.get("product_id")
            for record in records
            for item in record.get("items", [])
        }
        if product_id not in available_products:
            raise SyntheticProductNotFoundError(product_id)

        data_as_of = parse_daily_date(bundle.get("trained_through"))
        if data_as_of is None:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo model has no valid training cutoff."
            )

        try:
            forecast = predict_product_demand(
                bundle,
                records,
                product_id,
                data_as_of,
                horizon_days=horizon_days,
            )
        except InsufficientHistoryError:
            raise
        except Exception as exc:
            raise SyntheticForecastUnavailableError(
                "The synthetic demo forecast could not be generated."
            ) from exc

        return {
            **forecast,
            "is_synthetic_demo": True,
            "demo_label": "Synthetic demo forecast",
            "data_source": "synthetic development CSV",
            "data_as_of": data_as_of.isoformat(),
        }
