"""Testable training orchestration invoked by the training notebook."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import mlflow
import pandas as pd
import sklearn
from sklearn.pipeline import Pipeline

from online_shoppers.artifacts import ARTIFACT_SCHEMA_VERSION, ModelBundle, write_artifact
from online_shoppers.data import TARGET_COLUMN, dataset_summary, validate_dataset
from online_shoppers.features import model_feature_columns
from online_shoppers.modeling import (
    build_candidate_pipelines,
    evaluate_probabilities,
    select_champion,
    select_f1_threshold,
    split_dataset,
)
from online_shoppers.reporting import write_json
from online_shoppers.tracking import tracked_run


@dataclass(frozen=True)
class TrainingOutcome:
    """The decision and final metrics returned to the notebook."""

    champion_name: str
    include_page_values: bool
    threshold: float
    validation_metrics: dict[str, float | int]
    test_metrics: dict[str, float | int]


@dataclass
class _CandidateResult:
    name: str
    include_page_values: bool
    threshold: float
    metrics: dict[str, float | int]
    pipeline: Pipeline


def _metric_payload(prefix: str, values: dict[str, float | int]) -> dict[str, float]:
    return {f"{prefix}_{key}": float(value) for key, value in values.items()}


def train_champion(
    frame: pd.DataFrame,
    *,
    artifact_path: str | Path,
    metadata_path: str | Path,
    metrics_path: str | Path,
    tracking_uri: str,
    experiment_name: str = "online-shoppers-purchase-intention",
    random_seed: int = 42,
    forest_estimators: int = 300,
    git_revision: str = "local",
) -> TrainingOutcome:
    """Train all required candidates, select by validation F1, and evaluate test once."""

    validated = validate_dataset(frame)
    splits = split_dataset(validated, random_seed=random_seed)
    results: dict[str, _CandidateResult] = {}

    for include_page_values in (True, False):
        variant = "with_page_values" if include_page_values else "without_page_values"
        columns = model_feature_columns(include_page_values=include_page_values)
        candidates = build_candidate_pipelines(
            include_page_values=include_page_values,
            random_seed=random_seed,
            forest_estimators=forest_estimators,
        )
        for model_name, pipeline in candidates.items():
            result_name = f"{model_name}__{variant}"
            with tracked_run(
                tracking_uri=tracking_uri,
                experiment_name=experiment_name,
                run_name=result_name,
                params={
                    "model": model_name,
                    "include_page_values": include_page_values,
                    "random_seed": random_seed,
                    "selection_metric": "f1",
                },
            ):
                pipeline.fit(splits.train.loc[:, columns], splits.train[TARGET_COLUMN])
                validation_probabilities = pipeline.predict_proba(
                    splits.validation.loc[:, columns]
                )[:, 1]
                threshold = select_f1_threshold(
                    splits.validation[TARGET_COLUMN].to_numpy(), validation_probabilities
                )
                metrics = evaluate_probabilities(
                    splits.validation[TARGET_COLUMN], validation_probabilities, threshold
                )
                mlflow.log_metrics(_metric_payload("validation", metrics))
                mlflow.log_metric("threshold", threshold)
            results[result_name] = _CandidateResult(
                name=model_name,
                include_page_values=include_page_values,
                threshold=threshold,
                metrics=metrics,
                pipeline=pipeline,
            )

    champion_key = select_champion(
        {name: candidate.metrics for name, candidate in results.items()}, metric="f1"
    )
    champion = results[champion_key]
    champion_columns = model_feature_columns(include_page_values=champion.include_page_values)
    test_probabilities = champion.pipeline.predict_proba(splits.test.loc[:, champion_columns])[:, 1]
    test_metrics = evaluate_probabilities(
        splits.test[TARGET_COLUMN], test_probabilities, champion.threshold
    )
    model_version = git_revision
    bundle = ModelBundle(
        pipeline=champion.pipeline,
        feature_names=champion_columns,
        threshold=champion.threshold,
        schema_version=ARTIFACT_SCHEMA_VERSION,
        model_version=model_version,
    )
    metrics_payload: dict[str, Any] = {
        "champion": champion_key,
        "selection_metric": "f1",
        "validation": champion.metrics,
        "test": test_metrics,
        "candidates": {name: result.metrics for name, result in sorted(results.items())},
    }
    write_json(metrics_path, metrics_payload)
    metadata = write_artifact(
        bundle,
        artifact_path,
        metadata_path,
        {
            "trained_at": datetime.now(UTC).isoformat(),
            "git_revision": git_revision,
            "selection_metric": "f1",
            "champion": champion_key,
            "include_page_values": champion.include_page_values,
            "dataset": dataset_summary(validated),
            "validation_metrics": champion.metrics,
            "test_metrics": test_metrics,
            "versions": {
                "python": platform.python_version(),
                "scikit_learn": sklearn.__version__,
                "joblib": joblib.__version__,
            },
        },
    )
    write_json(metadata_path, metadata)

    with tracked_run(
        tracking_uri=tracking_uri,
        experiment_name=experiment_name,
        run_name="champion",
        params={
            "candidate": champion_key,
            "include_page_values": champion.include_page_values,
            "git_revision": git_revision,
            "selection_metric": "f1",
        },
    ):
        mlflow.log_metrics(_metric_payload("validation", champion.metrics))
        mlflow.log_metrics(_metric_payload("test", test_metrics))
        mlflow.log_metric("threshold", champion.threshold)
        mlflow.log_artifact(str(Path(artifact_path)))
        mlflow.log_artifact(str(Path(metadata_path)))
        mlflow.log_artifact(str(Path(metrics_path)))

    return TrainingOutcome(
        champion_name=champion.name,
        include_page_values=champion.include_page_values,
        threshold=champion.threshold,
        validation_metrics=champion.metrics,
        test_metrics=test_metrics,
    )
