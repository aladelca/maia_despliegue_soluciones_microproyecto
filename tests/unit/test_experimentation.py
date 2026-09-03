from __future__ import annotations

import numpy as np
import pandas as pd

from online_shoppers.data import TARGET_COLUMN
from online_shoppers.experimentation import (
    TorchMLPClassifier,
    build_candidate_specs,
    group_aware_split,
    session_group_ids,
)
from tests.unit.test_modeling import synthetic_dataset


def test_session_group_ids_match_for_identical_features() -> None:
    frame = synthetic_dataset(20)
    duplicate = frame.iloc[[0]].copy()
    duplicate[TARGET_COLUMN] = ~duplicate[TARGET_COLUMN]
    frame = pd.concat((frame, duplicate), ignore_index=True)

    groups = session_group_ids(frame)

    assert groups.iloc[0] == groups.iloc[-1]
    assert groups.nunique() == len(frame) - 1


def test_group_aware_split_keeps_duplicate_sessions_together() -> None:
    frame = synthetic_dataset(100)
    duplicates = frame.iloc[:10].copy()
    frame = pd.concat((frame, duplicates), ignore_index=True)

    split = group_aware_split(frame, random_seed=42, n_splits=5)

    assert set(split.development_groups).isdisjoint(split.audit_test_groups)
    assert len(split.development) + len(split.audit_test) == len(frame)
    assert set(split.development.columns) == set(frame.columns)
    assert abs(split.development[TARGET_COLUMN].mean() - frame[TARGET_COLUMN].mean()) < 0.05


def test_full_candidate_catalog_covers_all_required_families_and_five_folds() -> None:
    catalog = build_candidate_specs(profile="full", random_seed=42, positive_weight=5.0)

    assert catalog.n_splits == 5
    assert len(catalog.candidates) >= 40
    assert {
        "dummy",
        "logistic_regression",
        "random_forest",
        "extra_trees",
        "hist_gradient_boosting",
        "catboost",
        "xgboost",
        "lightgbm",
        "pytorch_mlp",
    }.issubset({candidate.family for candidate in catalog.candidates})
    assert all(candidate.name for candidate in catalog.candidates)


def test_torch_mlp_exports_numpy_only_inference_state() -> None:
    rng = np.random.default_rng(7)
    features = rng.normal(size=(40, 6)).astype(np.float32)
    target = np.array([False, True] * 20)
    classifier = TorchMLPClassifier(
        hidden_dims=(8,),
        max_epochs=3,
        batch_size=8,
        patience=2,
        random_state=42,
    )

    classifier.fit(features, target)
    probabilities = classifier.predict_proba(features)

    assert probabilities.shape == (40, 2)
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert classifier.training_device_ in {"mps", "cuda", "cpu"}
    assert not hasattr(classifier, "torch_model_")
    assert len(classifier.coefs_) == 2
