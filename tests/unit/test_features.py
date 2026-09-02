import pandas as pd
import pytest

from online_shoppers.data import FEATURE_COLUMNS
from online_shoppers.features import (
    SessionFeatureEngineer,
    build_preprocessor,
    engineered_feature_columns,
    model_feature_columns,
)


def feature_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            [
                0,
                0.0,
                0,
                0.0,
                1,
                5.0,
                0.20,
                0.20,
                0.0,
                0.0,
                "Feb",
                1,
                1,
                1,
                1,
                "Returning_Visitor",
                False,
            ],
            [
                2,
                20.0,
                1,
                4.0,
                8,
                80.0,
                0.01,
                0.02,
                15.0,
                0.2,
                "Nov",
                2,
                2,
                2,
                3,
                "New_Visitor",
                True,
            ],
        ],
        columns=FEATURE_COLUMNS,
    )


def test_preprocessor_keeps_shape_for_unknown_categories() -> None:
    train = feature_frame()
    unknown = train.iloc[[0]].copy()
    unknown["OperatingSystems"] = 99
    unknown["VisitorType"] = "Unknown_Visitor"

    preprocessor = build_preprocessor()
    transformed_train = preprocessor.fit_transform(train)
    transformed_unknown = preprocessor.transform(unknown)

    assert transformed_unknown.shape[1] == transformed_train.shape[1]


def test_feature_columns_can_exclude_page_values() -> None:
    columns = model_feature_columns(include_page_values=False)

    assert "PageValues" not in columns
    assert len(columns) == len(FEATURE_COLUMNS) - 1


@pytest.mark.parametrize("include_page_values", [True, False])
def test_session_feature_engineer_is_finite_and_respects_page_values(
    include_page_values: bool,
) -> None:
    train = feature_frame()
    train.loc[0, "ProductRelated"] = 0
    train.loc[0, "ProductRelated_Duration"] = 0
    transformed = SessionFeatureEngineer(
        include_page_values=include_page_values,
        rare_traffic_min_count=2,
    ).fit_transform(train)

    assert transformed.select_dtypes(include="number").notna().all(axis=None)
    assert (
        transformed.select_dtypes(include="number")
        .map(lambda value: abs(value) < float("inf"))
        .all(axis=None)
    )
    assert ("PageValues" in transformed.columns) is include_page_values
    assert ("page_values_log" in transformed.columns) is include_page_values
    assert set(engineered_feature_columns(include_page_values=include_page_values)).issubset(
        transformed.columns
    )


def test_session_feature_engineer_learns_rare_traffic_groups_from_training_only() -> None:
    train = feature_frame()
    train["TrafficType"] = [1, 1]
    unknown = train.iloc[[0]].copy()
    unknown["TrafficType"] = 99

    engineer = SessionFeatureEngineer(rare_traffic_min_count=2).fit(train)
    transformed = engineer.transform(unknown)

    assert transformed.iloc[0]["traffic_type_grouped"] == "rare"
