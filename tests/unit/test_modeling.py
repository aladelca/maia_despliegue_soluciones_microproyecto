import numpy as np
import pandas as pd
import pytest

from online_shoppers.data import FEATURE_COLUMNS, TARGET_COLUMN
from online_shoppers.modeling import (
    build_candidate_pipelines,
    evaluate_probabilities,
    select_champion,
    select_f1_threshold,
    split_dataset,
)


def synthetic_dataset(rows: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    revenue = np.array([False, True] * (rows // 2))
    return pd.DataFrame(
        {
            "Administrative": rng.integers(0, 5, rows),
            "Administrative_Duration": rng.uniform(0, 100, rows),
            "Informational": rng.integers(0, 3, rows),
            "Informational_Duration": rng.uniform(0, 50, rows),
            "ProductRelated": rng.integers(1, 20, rows),
            "ProductRelated_Duration": rng.uniform(1, 500, rows),
            "BounceRates": rng.uniform(0, 0.2, rows),
            "ExitRates": rng.uniform(0, 0.2, rows),
            "PageValues": revenue.astype(float) * 20 + rng.uniform(0, 1, rows),
            "SpecialDay": rng.choice([0.0, 0.2, 0.4], rows),
            "Month": rng.choice(["Feb", "Nov"], rows),
            "OperatingSystems": rng.choice([1, 2], rows),
            "Browser": rng.choice([1, 2], rows),
            "Region": rng.choice([1, 2], rows),
            "TrafficType": rng.choice([1, 2, 3], rows),
            "VisitorType": rng.choice(["Returning_Visitor", "New_Visitor"], rows),
            "Weekend": rng.choice([False, True], rows),
            TARGET_COLUMN: revenue,
        }
    )


def test_split_dataset_is_disjoint_stratified_and_deterministic() -> None:
    data = synthetic_dataset()

    first = split_dataset(data, random_seed=7)
    second = split_dataset(data, random_seed=7)

    assert (len(first.train), len(first.validation), len(first.test)) == (60, 20, 20)
    assert set(first.train.index).isdisjoint(first.validation.index)
    assert set(first.train.index).isdisjoint(first.test.index)
    assert first.train.index.tolist() == second.train.index.tolist()
    assert first.train[TARGET_COLUMN].mean() == pytest.approx(0.5)


def test_select_f1_threshold_uses_validation_probabilities() -> None:
    target = np.array([False, False, True, True])
    probabilities = np.array([0.10, 0.40, 0.45, 0.90])

    threshold = select_f1_threshold(target, probabilities)
    metrics = evaluate_probabilities(target, probabilities, threshold)

    assert threshold == pytest.approx(0.45)
    assert metrics["f1"] == pytest.approx(1.0)
    assert metrics["true_positive"] == 2
    assert metrics["false_positive"] == 0


def test_candidate_pipelines_fit_and_predict_probabilities() -> None:
    data = synthetic_dataset(40)
    candidates = build_candidate_pipelines(random_seed=42, forest_estimators=10)

    assert set(candidates) == {"dummy", "logistic_regression", "random_forest"}
    for pipeline in candidates.values():
        pipeline.fit(data.loc[:, FEATURE_COLUMNS], data[TARGET_COLUMN])
        probabilities = pipeline.predict_proba(data.loc[:, FEATURE_COLUMNS])[:, 1]
        assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_select_champion_uses_f1_and_stable_name_tiebreaker() -> None:
    results = {
        "random_forest": {"f1": 0.7, "pr_auc": 0.8},
        "logistic_regression": {"f1": 0.7, "pr_auc": 0.8},
        "dummy": {"f1": 0.1, "pr_auc": 0.5},
    }

    assert select_champion(results, metric="f1") == "logistic_regression"
