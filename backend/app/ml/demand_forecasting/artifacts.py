"""Persistence and validation for demand forecasting model bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.ml.demand_forecasting.features import FEATURE_VERSION


def persist_model(bundle: dict[str, Any], artifact_path: str | Path) -> Path:
    """Persist a model bundle at a caller-selected artifact path."""
    import joblib

    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


def load_model(artifact_path: str | Path) -> dict[str, Any]:
    """Load a compatible model bundle or fail with a stable error."""
    import joblib

    bundle = joblib.load(artifact_path)
    if not isinstance(bundle, dict) or bundle.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Unsupported or invalid demand model artifact.")
    return bundle
