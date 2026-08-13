import pandas as pd

from online_shoppers.data import FEATURE_COLUMNS
from online_shoppers.features import build_preprocessor, model_feature_columns


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
