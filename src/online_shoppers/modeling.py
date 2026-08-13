"""Model construction, splitting, threshold selection, and evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from online_shoppers.data import FEATURE_COLUMNS, TARGET_COLUMN
from online_shoppers.features import build_preprocessor


@dataclass(frozen=True)
class DatasetSplits:
    """Disjoint train, validation, and test frames."""

    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def split_dataset(frame: pd.DataFrame, *, random_seed: int = 42) -> DatasetSplits:
    """Create deterministic 60/20/20 stratified splits."""

    train, remainder = train_test_split(
        frame,
        test_size=0.4,
        random_state=random_seed,
        stratify=frame[TARGET_COLUMN],
    )
    validation, test = train_test_split(
        remainder,
        test_size=0.5,
        random_state=random_seed,
        stratify=remainder[TARGET_COLUMN],
    )
    return DatasetSplits(train=train, validation=validation, test=test)


def build_candidate_pipelines(
    *,
    include_page_values: bool = True,
    random_seed: int = 42,
    forest_estimators: int = 300,
) -> dict[str, Pipeline]:
    """Build the required baseline and two supervised candidates."""

    estimators = {
        "dummy": DummyClassifier(strategy="prior"),
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=random_seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=forest_estimators,
            min_samples_leaf=2,
            class_weight="balanced",
            n_jobs=-1,
            random_state=random_seed,
        ),
    }
    return {
        name: Pipeline(
            [
                ("preprocess", build_preprocessor(include_page_values=include_page_values)),
                ("classifier", estimator),
            ]
        )
        for name, estimator in estimators.items()
    }


def select_f1_threshold(target: np.ndarray, probabilities: np.ndarray) -> float:
    """Choose the validation threshold that maximizes binary F1."""

    precision, recall, thresholds = precision_recall_curve(target, probabilities)
    if thresholds.size == 0:
        return 0.5
    denominators = precision[:-1] + recall[:-1]
    scores = np.divide(
        2 * precision[:-1] * recall[:-1],
        denominators,
        out=np.zeros_like(denominators),
        where=denominators != 0,
    )
    return float(thresholds[int(np.argmax(scores))])


def evaluate_probabilities(
    target: np.ndarray | pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    """Compute imbalanced-class and calibration metrics at a threshold."""

    predictions = probabilities >= threshold
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        target, predictions, labels=[False, True]
    ).ravel()
    return {
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "pr_auc": float(average_precision_score(target, probabilities)),
        "precision": float(precision_score(target, predictions, zero_division=0)),
        "recall": float(recall_score(target, predictions, zero_division=0)),
        "f1": float(f1_score(target, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(target, probabilities)),
        "true_negative": int(true_negative),
        "false_positive": int(false_positive),
        "false_negative": int(false_negative),
        "true_positive": int(true_positive),
    }


def select_champion(results: Mapping[str, Mapping[str, float | int]], *, metric: str = "f1") -> str:
    """Select the best model with PR-AUC and name as deterministic tie-breakers."""

    if not results:
        raise ValueError("at least one model result is required")
    missing = sorted(name for name, values in results.items() if metric not in values)
    if missing:
        raise ValueError(f"metric {metric!r} is missing for: {missing}")
    return sorted(
        results,
        key=lambda name: (
            -float(results[name][metric]),
            -float(results[name].get("pr_auc", 0.0)),
            name,
        ),
    )[0]


def split_features_target(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return X/y using the canonical column order."""

    return frame.loc[:, FEATURE_COLUMNS], frame[TARGET_COLUMN]
