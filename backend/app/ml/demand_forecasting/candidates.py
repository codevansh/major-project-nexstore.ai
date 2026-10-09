"""Factories for comparable demand-forecasting model candidates."""

from __future__ import annotations

from typing import Any


def make_model_candidates(
    random_state: int = 42, n_estimators: int = 100
) -> dict[str, Any]:
    """Return estimators using the same feature dictionaries and target rows."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.pipeline import Pipeline

    return {
        "random_forest": Pipeline(
            steps=[
                ("vectorizer", DictVectorizer(sparse=True)),
                (
                    "regressor",
                    RandomForestRegressor(
                        n_estimators=n_estimators,
                        min_samples_leaf=2,
                        random_state=random_state,
                        n_jobs=1,
                    ),
                ),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            steps=[
                ("vectorizer", DictVectorizer(sparse=False)),
                (
                    "regressor",
                    HistGradientBoostingRegressor(
                        random_state=random_state,
                        max_iter=100,
                        learning_rate=0.1,
                        l2_regularization=1.0,
                    ),
                ),
            ]
        ),
    }
