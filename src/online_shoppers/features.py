"""Feature definitions and preprocessing pipelines."""

from __future__ import annotations

from typing import Self

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

from online_shoppers.data import (
    CATEGORICAL_COLUMNS,
    CONTINUOUS_COLUMNS,
    COUNT_COLUMNS,
    FEATURE_COLUMNS,
)

ENGINEERED_NUMERIC_COLUMNS = (
    "total_duration",
    "total_pageviews",
    "avg_duration_per_page",
    "administrative_duration_share",
    "product_duration_share",
    "bounce_exit_gap",
    "engagement_score",
    "administrative_duration_log",
    "informational_duration_log",
    "product_related_duration_log",
    "product_related_log",
    "has_special_day",
)
ENGINEERED_CATEGORICAL_COLUMNS = (
    "season_period",
    "traffic_type_grouped",
    "weekend_returning",
)


def model_feature_columns(*, include_page_values: bool = True) -> tuple[str, ...]:
    """Return the ordered inference columns for a model variant."""

    if include_page_values:
        return FEATURE_COLUMNS
    return tuple(column for column in FEATURE_COLUMNS if column != "PageValues")


def engineered_feature_columns(*, include_page_values: bool = True) -> tuple[str, ...]:
    """Return the deterministic output columns of :class:`SessionFeatureEngineer`."""

    numeric = list(ENGINEERED_NUMERIC_COLUMNS)
    if include_page_values:
        numeric.append("page_values_log")
    return (
        *model_feature_columns(include_page_values=include_page_values),
        *numeric,
        *ENGINEERED_CATEGORICAL_COLUMNS,
    )


class SessionFeatureEngineer(TransformerMixin, BaseEstimator):  # type: ignore[misc]
    """Create leakage-safe session features inside each fitted model pipeline."""

    def __init__(
        self,
        *,
        include_page_values: bool = True,
        rare_traffic_min_count: int = 100,
    ) -> None:
        self.include_page_values = include_page_values
        self.rare_traffic_min_count = rare_traffic_min_count

    def fit(self, frame: pd.DataFrame, target: object = None) -> Self:
        del target
        required = set(model_feature_columns(include_page_values=self.include_page_values))
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"missing feature columns: {missing}")
        if self.rare_traffic_min_count < 1:
            raise ValueError("rare_traffic_min_count must be positive")
        counts = frame["TrafficType"].value_counts()
        self.frequent_traffic_types_ = frozenset(
            counts[counts >= self.rare_traffic_min_count].index.tolist()
        )
        self.feature_names_out_ = engineered_feature_columns(
            include_page_values=self.include_page_values
        )
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, ("frequent_traffic_types_", "feature_names_out_"))
        selected = model_feature_columns(include_page_values=self.include_page_values)
        missing = sorted(set(selected) - set(frame.columns))
        if missing:
            raise ValueError(f"missing feature columns: {missing}")
        engineered = frame.loc[:, selected].copy()

        total_duration = (
            engineered["Administrative_Duration"]
            + engineered["Informational_Duration"]
            + engineered["ProductRelated_Duration"]
        )
        total_pageviews = (
            engineered["Administrative"]
            + engineered["Informational"]
            + engineered["ProductRelated"]
        )
        safe_duration = total_duration.replace(0, np.nan)
        safe_pageviews = total_pageviews.replace(0, np.nan)
        engineered["total_duration"] = total_duration
        engineered["total_pageviews"] = total_pageviews
        engineered["avg_duration_per_page"] = (total_duration / safe_pageviews).fillna(0.0)
        engineered["administrative_duration_share"] = (
            engineered["Administrative_Duration"] / safe_duration
        ).fillna(0.0)
        engineered["product_duration_share"] = (
            engineered["ProductRelated_Duration"] / safe_duration
        ).fillna(0.0)
        engineered["bounce_exit_gap"] = engineered["ExitRates"] - engineered["BounceRates"]
        engineered["engagement_score"] = engineered["ProductRelated_Duration"] * (
            1.0 - engineered["ExitRates"]
        )
        engineered["administrative_duration_log"] = np.log1p(engineered["Administrative_Duration"])
        engineered["informational_duration_log"] = np.log1p(engineered["Informational_Duration"])
        engineered["product_related_duration_log"] = np.log1p(engineered["ProductRelated_Duration"])
        engineered["product_related_log"] = np.log1p(engineered["ProductRelated"])
        engineered["has_special_day"] = (engineered["SpecialDay"] > 0).astype(float)
        if self.include_page_values:
            engineered["page_values_log"] = np.log1p(engineered["PageValues"])
        engineered["season_period"] = np.where(
            engineered["Month"].isin(("Nov", "Dec")), "holiday_peak", "regular"
        )
        engineered["traffic_type_grouped"] = (
            engineered["TrafficType"]
            .where(engineered["TrafficType"].isin(self.frequent_traffic_types_), other="rare")
            .astype(str)
        )
        engineered["weekend_returning"] = (
            engineered["Weekend"] & (engineered["VisitorType"].astype(str) == "Returning_Visitor")
        ).astype(str)
        return engineered.loc[:, self.feature_names_out_]

    def get_feature_names_out(self, input_features: object = None) -> np.ndarray:
        del input_features
        check_is_fitted(self, "feature_names_out_")
        return np.asarray(self.feature_names_out_, dtype=object)


def build_preprocessor(*, include_page_values: bool = True) -> ColumnTransformer:
    """Build preprocessing that is fitted only as part of an sklearn Pipeline."""

    selected = set(model_feature_columns(include_page_values=include_page_values))
    numeric_columns = [
        column for column in (*COUNT_COLUMNS, *CONTINUOUS_COLUMNS) if column in selected
    ]
    categorical_columns = [column for column in CATEGORICAL_COLUMNS if column in selected]

    numeric_pipeline = Pipeline([("scale", StandardScaler())])
    categorical_pipeline = Pipeline(
        [("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=True))]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
    )


def build_engineered_preprocessor(*, include_page_values: bool = True) -> ColumnTransformer:
    """Build the dense preprocessor used by the cross-family experiment catalog."""

    selected = set(model_feature_columns(include_page_values=include_page_values))
    numeric_columns = [
        column for column in (*COUNT_COLUMNS, *CONTINUOUS_COLUMNS) if column in selected
    ]
    numeric_columns.extend(ENGINEERED_NUMERIC_COLUMNS)
    if include_page_values:
        numeric_columns.append("page_values_log")
    categorical_columns = [column for column in CATEGORICAL_COLUMNS if column in selected]
    categorical_columns.extend(ENGINEERED_CATEGORICAL_COLUMNS)
    return ColumnTransformer(
        transformers=[
            ("numeric", Pipeline([("scale", StandardScaler())]), numeric_columns),
            (
                "categorical",
                Pipeline([("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
                categorical_columns,
            ),
        ],
        remainder="drop",
    )
