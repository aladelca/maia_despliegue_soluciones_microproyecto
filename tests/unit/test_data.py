from pathlib import Path

import pandas as pd
import pytest

from online_shoppers.data import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    DataValidationError,
    dataset_summary,
    load_dataset,
    validate_dataset,
)


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Administrative": 0,
                "Administrative_Duration": 0.0,
                "Informational": 0,
                "Informational_Duration": 0.0,
                "ProductRelated": 1,
                "ProductRelated_Duration": 15.0,
                "BounceRates": 0.2,
                "ExitRates": 0.2,
                "PageValues": 0.0,
                "SpecialDay": 0.0,
                "Month": "Feb",
                "OperatingSystems": 1,
                "Browser": 1,
                "Region": 1,
                "TrafficType": 1,
                "VisitorType": "Returning_Visitor",
                "Weekend": "FALSE",
                "Revenue": "FALSE",
            },
            {
                "Administrative": 2,
                "Administrative_Duration": 30.0,
                "Informational": 1,
                "Informational_Duration": 5.0,
                "ProductRelated": 8,
                "ProductRelated_Duration": 120.0,
                "BounceRates": 0.01,
                "ExitRates": 0.02,
                "PageValues": 20.0,
                "SpecialDay": 0.2,
                "Month": "Nov",
                "OperatingSystems": 2,
                "Browser": 2,
                "Region": 2,
                "TrafficType": 3,
                "VisitorType": "New_Visitor",
                "Weekend": "TRUE",
                "Revenue": "TRUE",
            },
        ]
    )


def test_validate_dataset_normalizes_boolean_columns() -> None:
    validated = validate_dataset(valid_frame())

    assert list(validated.columns) == [*FEATURE_COLUMNS, TARGET_COLUMN]
    assert validated["Weekend"].tolist() == [False, True]
    assert validated[TARGET_COLUMN].tolist() == [False, True]
    assert str(validated["Weekend"].dtype) == "bool"


@pytest.mark.parametrize("column", ["Revenue", "Month"])
def test_validate_dataset_rejects_missing_columns(column: str) -> None:
    frame = valid_frame().drop(columns=[column])

    with pytest.raises(DataValidationError, match="missing columns"):
        validate_dataset(frame)


def test_validate_dataset_rejects_extra_columns() -> None:
    frame = valid_frame().assign(SessionId=[1, 2])

    with pytest.raises(DataValidationError, match="unexpected columns"):
        validate_dataset(frame)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("Administrative", -1, "non-negative"),
        ("BounceRates", 1.1, "between 0 and 1"),
        ("SpecialDay", -0.1, "between 0 and 1"),
        ("Month", "Jan", "unknown categories"),
        ("VisitorType", "Robot", "unknown categories"),
    ],
)
def test_validate_dataset_rejects_invalid_values(column: str, value: object, message: str) -> None:
    frame = valid_frame()
    frame.at[0, column] = value  # type: ignore[assignment]

    with pytest.raises(DataValidationError, match=message):
        validate_dataset(frame)


def test_validate_dataset_rejects_single_target_class() -> None:
    frame = valid_frame()
    frame["Revenue"] = False

    with pytest.raises(DataValidationError, match="two target classes"):
        validate_dataset(frame)


def test_dataset_summary_reports_duplicates_without_dropping_them() -> None:
    frame = pd.concat([valid_frame(), valid_frame().iloc[[0]]], ignore_index=True)
    validated = validate_dataset(frame)

    summary = dataset_summary(validated)

    assert len(validated) == 3
    assert summary == {
        "rows": 3,
        "columns": 18,
        "duplicate_rows": 1,
        "positive_count": 1,
        "positive_rate": pytest.approx(1 / 3),
    }


def test_load_dataset_reads_and_validates_csv(tmp_path: Path) -> None:
    path = tmp_path / "sessions.csv"
    valid_frame().to_csv(path, index=False)

    loaded = load_dataset(path)

    assert loaded.shape == (2, 18)
    assert loaded["Revenue"].tolist() == [False, True]
