"""Feature definitions and preprocessing pipelines."""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from online_shoppers.data import (
    CATEGORICAL_COLUMNS,
    CONTINUOUS_COLUMNS,
    COUNT_COLUMNS,
    FEATURE_COLUMNS,
)


def model_feature_columns(*, include_page_values: bool = True) -> tuple[str, ...]:
    """Return the ordered inference columns for a model variant."""

    if include_page_values:
        return FEATURE_COLUMNS
    return tuple(column for column in FEATURE_COLUMNS if column != "PageValues")


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
