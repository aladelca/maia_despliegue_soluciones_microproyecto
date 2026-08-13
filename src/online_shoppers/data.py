"""Dataset loading and validation for the UCI online-shoppers data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

COUNT_COLUMNS = ("Administrative", "Informational", "ProductRelated")
DURATION_COLUMNS = (
    "Administrative_Duration",
    "Informational_Duration",
    "ProductRelated_Duration",
)
RATE_COLUMNS = ("BounceRates", "ExitRates", "SpecialDay")
CONTINUOUS_COLUMNS = (*DURATION_COLUMNS, *RATE_COLUMNS, "PageValues")
CATEGORICAL_CODE_COLUMNS = ("OperatingSystems", "Browser", "Region", "TrafficType")
CATEGORICAL_COLUMNS = (*CATEGORICAL_CODE_COLUMNS, "Month", "VisitorType", "Weekend")
FEATURE_COLUMNS = (
    "Administrative",
    "Administrative_Duration",
    "Informational",
    "Informational_Duration",
    "ProductRelated",
    "ProductRelated_Duration",
    "BounceRates",
    "ExitRates",
    "PageValues",
    "SpecialDay",
    "Month",
    "OperatingSystems",
    "Browser",
    "Region",
    "TrafficType",
    "VisitorType",
    "Weekend",
)
TARGET_COLUMN = "Revenue"
EXPECTED_COLUMNS = (*FEATURE_COLUMNS, TARGET_COLUMN)
KNOWN_MONTHS = frozenset({"Feb", "Mar", "May", "June", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"})
KNOWN_VISITOR_TYPES = frozenset({"New_Visitor", "Returning_Visitor", "Other"})


class DataValidationError(ValueError):
    """Raised when a dataset violates the training-data contract."""


def _parse_boolean(value: Any, column: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized == "TRUE":
            return True
        if normalized == "FALSE":
            return False
    raise DataValidationError(f"{column} contains a value that is not boolean: {value!r}")


def _coerce_numeric(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"{column} must be numeric") from exc


def _validate_categories(frame: pd.DataFrame, column: str, known: frozenset[str]) -> None:
    actual = set(frame[column].astype(str).unique())
    unknown = sorted(actual - known)
    if unknown:
        raise DataValidationError(f"{column} contains unknown categories: {unknown}")


def validate_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a normalized copy of a frame that satisfies the dataset contract."""

    actual_columns = set(frame.columns)
    expected_columns = set(EXPECTED_COLUMNS)
    missing = sorted(expected_columns - actual_columns)
    unexpected = sorted(actual_columns - expected_columns)
    if missing:
        raise DataValidationError(f"missing columns: {missing}")
    if unexpected:
        raise DataValidationError(f"unexpected columns: {unexpected}")

    validated = frame.loc[:, EXPECTED_COLUMNS].copy()
    if validated.empty:
        raise DataValidationError("dataset must contain at least one row")
    if validated.isna().any(axis=None):
        null_columns = sorted(validated.columns[validated.isna().any()].tolist())
        raise DataValidationError(f"null values found in columns: {null_columns}")

    validated["Weekend"] = validated["Weekend"].map(lambda value: _parse_boolean(value, "Weekend"))
    validated[TARGET_COLUMN] = validated[TARGET_COLUMN].map(
        lambda value: _parse_boolean(value, TARGET_COLUMN)
    )

    numeric_columns = (*COUNT_COLUMNS, *CONTINUOUS_COLUMNS, *CATEGORICAL_CODE_COLUMNS)
    _coerce_numeric(validated, numeric_columns)

    non_negative_columns = (*COUNT_COLUMNS, *DURATION_COLUMNS, "PageValues")
    for column in non_negative_columns:
        if (validated[column] < 0).any():
            raise DataValidationError(f"{column} must be non-negative")

    for column in RATE_COLUMNS:
        if (~validated[column].between(0, 1, inclusive="both")).any():
            raise DataValidationError(f"{column} must be between 0 and 1")

    integer_columns = (*COUNT_COLUMNS, *CATEGORICAL_CODE_COLUMNS)
    for column in integer_columns:
        values = validated[column]
        if (values % 1 != 0).any():
            raise DataValidationError(f"{column} must contain integers")
        if column in CATEGORICAL_CODE_COLUMNS and (values < 1).any():
            raise DataValidationError(f"{column} must contain positive category codes")
        validated[column] = values.astype("int64")

    _validate_categories(validated, "Month", KNOWN_MONTHS)
    _validate_categories(validated, "VisitorType", KNOWN_VISITOR_TYPES)
    if validated[TARGET_COLUMN].nunique() != 2:
        raise DataValidationError("dataset must contain two target classes")

    return validated


def load_dataset(path: str | Path) -> pd.DataFrame:
    """Load a CSV file and enforce the full training-data contract."""

    return validate_dataset(pd.read_csv(Path(path)))


def dataset_summary(frame: pd.DataFrame) -> dict[str, int | float]:
    """Create the compact quality summary used by notebooks and reports."""

    positive_count = int(frame[TARGET_COLUMN].sum())
    return {
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "duplicate_rows": int(frame.duplicated().sum()),
        "positive_count": positive_count,
        "positive_rate": positive_count / int(frame.shape[0]),
    }
