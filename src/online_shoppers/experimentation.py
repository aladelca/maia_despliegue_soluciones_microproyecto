"""Reproducible candidate catalog and primitives for the EC2 experiment campaign."""

from __future__ import annotations

import platform
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.pipeline import Pipeline

from online_shoppers.artifacts import ARTIFACT_SCHEMA_VERSION, ModelBundle, write_artifact
from online_shoppers.data import FEATURE_COLUMNS, TARGET_COLUMN, dataset_summary, validate_dataset
from online_shoppers.features import (
    SessionFeatureEngineer,
    build_engineered_preprocessor,
    build_preprocessor,
    model_feature_columns,
)
from online_shoppers.modeling import evaluate_probabilities, select_f1_threshold
from online_shoppers.reporting import write_json


@dataclass(frozen=True)
class GroupAwareSplit:
    """Development and sealed audit partitions with their duplicate-session groups."""

    development: pd.DataFrame
    audit_test: pd.DataFrame
    development_groups: pd.Series
    audit_test_groups: pd.Series


@dataclass(frozen=True)
class CandidateSpec:
    """A single, named model configuration evaluated as one MLflow run."""

    name: str
    family: str
    feature_set: str
    params: dict[str, Any]


@dataclass(frozen=True)
class CandidateCatalog:
    """The immutable configurations and validation policy for a campaign profile."""

    n_splits: int
    candidates: tuple[CandidateSpec, ...]


@dataclass(frozen=True)
class CampaignPaths:
    """All versioned and materialized outputs produced by one campaign."""

    artifact_path: Path
    metadata_path: Path
    metrics_path: Path
    comparison_path: Path
    protocol_path: Path
    tracking_artifacts_dir: Path


@dataclass(frozen=True)
class CampaignOutcome:
    """The final selection and remote run identity returned to callers."""

    champion_name: str
    champion_run_id: str
    threshold: float
    validation_metrics: dict[str, float | int]
    test_metrics: dict[str, float | int]


@dataclass(frozen=True)
class _CandidateEvaluation:
    spec: CandidateSpec
    run_id: str
    threshold: float
    metrics: dict[str, float]
    fold_metrics: tuple[dict[str, float], ...]


def session_group_ids(frame: pd.DataFrame) -> pd.Series:
    """Hash raw input features so identical sessions cannot cross partitions."""

    missing = sorted(set(FEATURE_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing feature columns: {missing}")
    hashes = pd.util.hash_pandas_object(frame.loc[:, FEATURE_COLUMNS], index=False)
    return hashes.astype("uint64").astype(str).rename("session_group")


def group_aware_split(
    frame: pd.DataFrame,
    *,
    random_seed: int = 42,
    n_splits: int = 5,
) -> GroupAwareSplit:
    """Reserve one stratified group fold as a sealed audit set."""

    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")
    groups = session_group_ids(frame)
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_seed)
    development_positions, audit_positions = next(
        splitter.split(frame.loc[:, FEATURE_COLUMNS], frame[TARGET_COLUMN], groups)
    )
    development = frame.iloc[development_positions].copy()
    audit_test = frame.iloc[audit_positions].copy()
    return GroupAwareSplit(
        development=development,
        audit_test=audit_test,
        development_groups=groups.iloc[development_positions].copy(),
        audit_test_groups=groups.iloc[audit_positions].copy(),
    )


def _specs_for_feature_set(
    feature_set: str,
    *,
    random_seed: int,
    positive_weight: float,
) -> list[CandidateSpec]:
    specs: list[CandidateSpec] = []

    def add(family: str, suffix: str, **params: Any) -> None:
        specs.append(
            CandidateSpec(
                name=f"{family}__{feature_set}__{suffix}",
                family=family,
                feature_set=feature_set,
                params={"random_seed": random_seed, **params},
            )
        )

    add("dummy", "prior", strategy="prior")
    for c_value in (0.05, 0.2, 1.0):
        add("logistic_regression", f"c_{c_value:g}", c=c_value)
    for estimators, leaf in ((300, 1), (300, 3), (600, 1), (600, 3)):
        add("random_forest", f"n_{estimators}_leaf_{leaf}", n_estimators=estimators, min_leaf=leaf)
        add("extra_trees", f"n_{estimators}_leaf_{leaf}", n_estimators=estimators, min_leaf=leaf)
    for learning_rate, leaf_nodes, l2 in (
        (0.03, 15, 0.0),
        (0.05, 31, 0.0),
        (0.08, 31, 1.0),
        (0.05, 63, 1.0),
    ):
        add(
            "hist_gradient_boosting",
            f"lr_{learning_rate:g}_leaves_{leaf_nodes}_l2_{l2:g}",
            learning_rate=learning_rate,
            max_leaf_nodes=leaf_nodes,
            l2_regularization=l2,
        )
    for depth, learning_rate, l2 in (
        (4, 0.03, 3),
        (4, 0.06, 7),
        (6, 0.03, 3),
        (6, 0.06, 7),
        (8, 0.03, 5),
        (8, 0.05, 9),
    ):
        add(
            "catboost",
            f"depth_{depth}_lr_{learning_rate:g}_l2_{l2}",
            depth=depth,
            learning_rate=learning_rate,
            l2_leaf_reg=l2,
            positive_weight=positive_weight,
        )
    for depth, learning_rate, child_weight in (
        (3, 0.03, 1),
        (4, 0.05, 1),
        (5, 0.03, 3),
        (6, 0.05, 5),
    ):
        add(
            "xgboost",
            f"depth_{depth}_lr_{learning_rate:g}_child_{child_weight}",
            max_depth=depth,
            learning_rate=learning_rate,
            min_child_weight=child_weight,
            positive_weight=positive_weight,
        )
    for leaves, learning_rate, min_child in (
        (15, 0.03, 20),
        (31, 0.05, 20),
        (63, 0.03, 30),
        (31, 0.08, 40),
    ):
        add(
            "lightgbm",
            f"leaves_{leaves}_lr_{learning_rate:g}_child_{min_child}",
            num_leaves=leaves,
            learning_rate=learning_rate,
            min_child_samples=min_child,
        )
    for hidden_dims, learning_rate, weight_decay in (
        ((64, 32), 1e-3, 1e-4),
        ((128, 64), 5e-4, 1e-4),
        ((128, 64, 32), 1e-3, 1e-3),
    ):
        hidden_slug = "x".join(str(value) for value in hidden_dims)
        add(
            "pytorch_mlp",
            f"hidden_{hidden_slug}_lr_{learning_rate:g}_wd_{weight_decay:g}",
            hidden_dims=hidden_dims,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
        )
    return specs


def build_candidate_specs(
    *,
    profile: str,
    random_seed: int,
    positive_weight: float,
) -> CandidateCatalog:
    """Build the bounded smoke or full experiment catalog."""

    if profile not in {"smoke", "full"}:
        raise ValueError("profile must be 'smoke' or 'full'")
    if profile == "smoke":
        return CandidateCatalog(
            n_splits=2,
            candidates=(
                CandidateSpec(
                    name="dummy__base_with_page_values__prior",
                    family="dummy",
                    feature_set="base_with_page_values",
                    params={"strategy": "prior", "random_seed": random_seed},
                ),
                CandidateSpec(
                    name="logistic_regression__engineered_with_page_values__c_1",
                    family="logistic_regression",
                    feature_set="engineered_with_page_values",
                    params={"c": 1.0, "random_seed": random_seed},
                ),
            ),
        )
    candidates: list[CandidateSpec] = []
    for feature_set in ("engineered_with_page_values", "engineered_without_page_values"):
        candidates.extend(
            _specs_for_feature_set(
                feature_set,
                random_seed=random_seed,
                positive_weight=positive_weight,
            )
        )
    return CandidateCatalog(n_splits=5, candidates=tuple(candidates))


class TorchMLPClassifier(ClassifierMixin, BaseEstimator):  # type: ignore[misc]
    """Train with PyTorch, then export NumPy weights for lightweight inference."""

    def __init__(
        self,
        *,
        hidden_dims: tuple[int, ...] = (64, 32),
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 80,
        batch_size: int = 256,
        patience: int = 10,
        validation_fraction: float = 0.15,
        random_state: int = 42,
    ) -> None:
        self.hidden_dims = hidden_dims
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.batch_size = batch_size
        self.patience = patience
        self.validation_fraction = validation_fraction
        self.random_state = random_state

    def fit(self, features: Any, target: Any) -> Self:
        try:
            import torch
            from torch import nn
            from torch.utils.data import DataLoader, TensorDataset
        except (
            ImportError
        ) as exc:  # pragma: no cover - exercised by deployment without training deps
            raise RuntimeError("PyTorch is required to fit TorchMLPClassifier") from exc

        matrix = np.asarray(features, dtype=np.float32)
        labels = np.asarray(target, dtype=np.float32)
        if matrix.ndim != 2 or len(matrix) != len(labels):
            raise ValueError("features and target must have compatible two-dimensional shapes")
        if np.unique(labels).size != 2:
            raise ValueError("TorchMLPClassifier requires a binary target")
        if not self.hidden_dims or any(width < 1 for width in self.hidden_dims):
            raise ValueError("hidden_dims must contain positive layer widths")

        torch.manual_seed(self.random_state)
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        elif torch.cuda.is_available():
            device = torch.device("cuda")
        else:
            device = torch.device("cpu")
        self.training_device_ = device.type
        self.n_features_in_ = matrix.shape[1]
        self.classes_ = np.asarray([False, True])

        train_x, validation_x, train_y, validation_y = train_test_split(
            matrix,
            labels,
            test_size=self.validation_fraction,
            stratify=labels,
            random_state=self.random_state,
        )
        layers: list[nn.Module] = []
        input_width = self.n_features_in_
        for hidden_width in self.hidden_dims:
            layers.extend((nn.Linear(input_width, hidden_width), nn.ReLU()))
            input_width = hidden_width
        layers.append(nn.Linear(input_width, 1))
        model = nn.Sequential(*layers).to(device)

        positive_count = max(float(train_y.sum()), 1.0)
        negative_count = max(float(len(train_y) - train_y.sum()), 1.0)
        loss_function = nn.BCEWithLogitsLoss(
            pos_weight=torch.tensor([negative_count / positive_count], device=device)
        )
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay
        )
        generator = torch.Generator().manual_seed(self.random_state)
        loader = DataLoader(
            TensorDataset(torch.from_numpy(train_x), torch.from_numpy(train_y)),
            batch_size=min(self.batch_size, len(train_x)),
            shuffle=True,
            generator=generator,
        )
        validation_features = torch.from_numpy(validation_x).to(device)
        validation_target = torch.from_numpy(validation_y).to(device)
        best_loss = float("inf")
        best_state: dict[str, Any] | None = None
        stale_epochs = 0
        self.epochs_trained_ = 0
        for epoch in range(self.max_epochs):
            model.train()
            for batch_features, batch_target in loader:
                optimizer.zero_grad(set_to_none=True)
                logits = model(batch_features.to(device)).squeeze(1)
                loss = loss_function(logits, batch_target.to(device))
                loss.backward()
                optimizer.step()
            model.eval()
            with torch.no_grad():
                validation_logits = model(validation_features).squeeze(1)
                validation_loss = float(loss_function(validation_logits, validation_target).item())
            self.epochs_trained_ = epoch + 1
            if validation_loss < best_loss - 1e-6:
                best_loss = validation_loss
                best_state = {
                    name: value.detach().cpu().clone() for name, value in model.state_dict().items()
                }
                stale_epochs = 0
            else:
                stale_epochs += 1
                if stale_epochs >= self.patience:
                    break
        if best_state is None:
            raise RuntimeError("PyTorch training did not produce a valid state")
        model.load_state_dict(best_state)
        model.to("cpu")

        self.coefs_ = []
        self.intercepts_ = []
        for layer in model:
            if isinstance(layer, nn.Linear):
                self.coefs_.append(layer.weight.detach().numpy().T.copy())
                self.intercepts_.append(layer.bias.detach().numpy().copy())
        self.best_validation_loss_ = best_loss
        return self

    def predict_proba(self, features: Any) -> np.ndarray:
        if not hasattr(self, "coefs_"):
            raise ValueError("TorchMLPClassifier must be fitted before prediction")
        activations = np.asarray(features, dtype=np.float32)
        for weights, bias in zip(self.coefs_[:-1], self.intercepts_[:-1], strict=True):
            activations = np.maximum(activations @ weights + bias, 0.0)
        logits = (activations @ self.coefs_[-1] + self.intercepts_[-1]).reshape(-1)
        positive = np.empty_like(logits, dtype=np.float64)
        non_negative = logits >= 0
        positive[non_negative] = 1.0 / (1.0 + np.exp(-logits[non_negative]))
        exp_values = np.exp(logits[~non_negative])
        positive[~non_negative] = exp_values / (1.0 + exp_values)
        return np.column_stack((1.0 - positive, positive))

    def predict(self, features: Any) -> np.ndarray:
        return self.predict_proba(features)[:, 1] >= 0.5


def _feature_set_flags(feature_set: str) -> tuple[bool, bool]:
    known = {
        "base_with_page_values": (False, True),
        "base_without_page_values": (False, False),
        "engineered_with_page_values": (True, True),
        "engineered_without_page_values": (True, False),
    }
    try:
        return known[feature_set]
    except KeyError as exc:
        raise ValueError(f"unknown feature set: {feature_set}") from exc


def _build_estimator(spec: CandidateSpec) -> Any:
    params = dict(spec.params)
    random_seed = int(params.pop("random_seed"))
    family = spec.family
    if family == "dummy":
        return DummyClassifier(strategy=str(params["strategy"]))
    if family == "logistic_regression":
        return LogisticRegression(
            C=float(params["c"]),
            class_weight="balanced",
            max_iter=2000,
            random_state=random_seed,
        )
    if family == "random_forest":
        return RandomForestClassifier(
            n_estimators=int(params["n_estimators"]),
            min_samples_leaf=int(params["min_leaf"]),
            class_weight="balanced",
            n_jobs=-1,
            random_state=random_seed,
        )
    if family == "extra_trees":
        return ExtraTreesClassifier(
            n_estimators=int(params["n_estimators"]),
            min_samples_leaf=int(params["min_leaf"]),
            class_weight="balanced",
            n_jobs=-1,
            random_state=random_seed,
        )
    if family == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]),
            max_leaf_nodes=int(params["max_leaf_nodes"]),
            l2_regularization=float(params["l2_regularization"]),
            max_iter=350,
            class_weight="balanced",
            random_state=random_seed,
        )
    if family == "catboost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(
            iterations=500,
            depth=int(params["depth"]),
            learning_rate=float(params["learning_rate"]),
            l2_leaf_reg=float(params["l2_leaf_reg"]),
            scale_pos_weight=float(params["positive_weight"]),
            loss_function="Logloss",
            eval_metric="PRAUC",
            random_seed=random_seed,
            verbose=False,
            allow_writing_files=False,
            thread_count=-1,
        )
    if family == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=500,
            max_depth=int(params["max_depth"]),
            learning_rate=float(params["learning_rate"]),
            min_child_weight=float(params["min_child_weight"]),
            subsample=0.85,
            colsample_bytree=0.85,
            scale_pos_weight=float(params["positive_weight"]),
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=-1,
            random_state=random_seed,
        )
    if family == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=500,
            num_leaves=int(params["num_leaves"]),
            learning_rate=float(params["learning_rate"]),
            min_child_samples=int(params["min_child_samples"]),
            subsample=0.85,
            colsample_bytree=0.85,
            class_weight="balanced",
            random_state=random_seed,
            n_jobs=-1,
            verbosity=-1,
        )
    if family == "pytorch_mlp":
        return TorchMLPClassifier(
            hidden_dims=tuple(int(width) for width in params["hidden_dims"]),
            learning_rate=float(params["learning_rate"]),
            weight_decay=float(params["weight_decay"]),
            max_epochs=80,
            batch_size=256,
            patience=10,
            random_state=random_seed,
        )
    raise ValueError(f"unsupported model family: {family}")


def build_experiment_pipeline(spec: CandidateSpec) -> Pipeline:
    """Build one serializable preprocessing and classifier pipeline."""

    engineered, include_page_values = _feature_set_flags(spec.feature_set)
    steps: list[tuple[str, Any]] = []
    if engineered:
        steps.append(
            (
                "feature_engineering",
                SessionFeatureEngineer(
                    include_page_values=include_page_values,
                    rare_traffic_min_count=100,
                ),
            )
        )
        preprocessor = build_engineered_preprocessor(include_page_values=include_page_values)
    else:
        preprocessor = build_preprocessor(include_page_values=include_page_values)
        preprocessor.set_params(categorical__encode__sparse_output=False)
    steps.extend((("preprocess", preprocessor), ("classifier", _build_estimator(spec))))
    return Pipeline(steps)


def _normalized_params(spec: CandidateSpec) -> dict[str, str]:
    return {
        "candidate_name": spec.name,
        "family": spec.family,
        "feature_set": spec.feature_set,
        **{key: str(value) for key, value in sorted(spec.params.items())},
    }


def _metric_means(folds: list[dict[str, float]]) -> dict[str, float]:
    keys = ("pr_auc", "roc_auc", "f1", "precision", "recall", "brier_score")
    result: dict[str, float] = {}
    for key in keys:
        values = np.asarray([fold[key] for fold in folds], dtype=float)
        result[f"cv_{key}_mean"] = float(values.mean())
        result[f"cv_{key}_std"] = float(values.std(ddof=0))
    return result


def _evaluate_candidate(
    spec: CandidateSpec,
    development: pd.DataFrame,
    groups: pd.Series,
    *,
    n_splits: int,
    random_seed: int,
) -> tuple[dict[str, float], tuple[dict[str, float], ...], float]:
    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=random_seed,
    )
    target = development[TARGET_COLUMN].to_numpy()
    oof_probabilities = np.full(len(development), np.nan, dtype=float)
    fold_metrics: list[dict[str, float]] = []
    include_page_values = _feature_set_flags(spec.feature_set)[1]
    columns = model_feature_columns(include_page_values=include_page_values)
    started_at = time.perf_counter()
    for fold_index, (train_positions, validation_positions) in enumerate(
        splitter.split(development.loc[:, columns], target, groups)
    ):
        pipeline = build_experiment_pipeline(spec)
        pipeline.fit(
            development.iloc[train_positions].loc[:, columns],
            target[train_positions],
        )
        probabilities = pipeline.predict_proba(
            development.iloc[validation_positions].loc[:, columns]
        )[:, 1]
        oof_probabilities[validation_positions] = probabilities
        fold_values = evaluate_probabilities(
            target[validation_positions], probabilities, threshold=0.5
        )
        fold_metrics.append(
            {
                "fold": float(fold_index),
                **{key: float(value) for key, value in fold_values.items()},
            }
        )
    if np.isnan(oof_probabilities).any():
        raise RuntimeError(f"candidate {spec.name} did not produce all OOF probabilities")
    threshold = select_f1_threshold(target, oof_probabilities)
    oof = evaluate_probabilities(target, oof_probabilities, threshold)
    metrics = _metric_means(fold_metrics)
    metrics.update({f"oof_{key}": float(value) for key, value in oof.items()})
    metrics["threshold"] = threshold
    metrics["duration_seconds"] = time.perf_counter() - started_at
    return metrics, tuple(fold_metrics), threshold


@contextmanager
def _tracking_context(tracking_uri: str) -> Iterator[None]:
    import mlflow

    previous_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    try:
        yield
    finally:
        mlflow.set_tracking_uri(previous_uri)


def _prepare_experiment(
    tracking_uri: str,
    experiment_name: str,
    artifact_directory: Path,
) -> str:
    import mlflow
    from mlflow import MlflowClient

    client = MlflowClient(tracking_uri=tracking_uri)
    existing = client.get_experiment_by_name(experiment_name)
    if existing is None:
        artifact_location: str | None = None
        if tracking_uri.startswith("sqlite:"):
            artifact_directory.mkdir(parents=True, exist_ok=True)
            artifact_location = artifact_directory.resolve().as_uri()
        experiment_id = client.create_experiment(
            experiment_name,
            artifact_location=artifact_location,
        )
    else:
        experiment_id = existing.experiment_id
    mlflow.set_experiment(experiment_name)
    return experiment_id


def _log_registered_model(
    pipeline: Pipeline,
    input_example: pd.DataFrame,
    *,
    registered_model_name: str | None,
    champion_run_id: str,
) -> None:
    import mlflow
    import mlflow.sklearn
    from mlflow import MlflowClient
    from mlflow.models import infer_signature

    signature = infer_signature(input_example, pipeline.predict_proba(input_example))
    mlflow.sklearn.log_model(
        sk_model=pipeline,
        name="model",
        signature=signature,
        input_example=input_example.head(3),
        registered_model_name=registered_model_name,
        serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
    )
    if registered_model_name is None:
        return
    client = MlflowClient()
    versions = [
        version
        for version in client.search_model_versions(f"name='{registered_model_name}'")
        if version.run_id == champion_run_id
    ]
    if not versions:
        raise RuntimeError("registered model version was not created for the champion run")
    selected = max(versions, key=lambda version: int(version.version))
    client.set_registered_model_alias(registered_model_name, "champion", selected.version)


def run_experiment_campaign(
    frame: pd.DataFrame,
    *,
    tracking_uri: str,
    paths: CampaignPaths,
    profile: str,
    experiment_name: str,
    registered_model_name: str | None,
    git_revision: str,
    data_version: str,
    random_seed: int = 42,
) -> CampaignOutcome:
    """Evaluate every configured run, select once, and package the audit-tested champion."""

    import mlflow

    validated = validate_dataset(frame)
    split = group_aware_split(validated, random_seed=random_seed, n_splits=5)
    development = split.development
    target = development[TARGET_COLUMN]
    positive_count = int(target.sum())
    negative_count = len(target) - positive_count
    positive_weight = negative_count / max(positive_count, 1)
    catalog = build_candidate_specs(
        profile=profile,
        random_seed=random_seed,
        positive_weight=positive_weight,
    )
    protocol = {
        "random_seed": random_seed,
        "audit_strategy": "first_stratified_group_fold_of_5",
        "cv_strategy": f"StratifiedGroupKFold({catalog.n_splits})",
        "selection_metric": "cv_pr_auc_mean",
        "threshold_metric": "oof_f1",
        "dataset_rows": len(validated),
        "development_rows": len(development),
        "audit_test_rows": len(split.audit_test),
        "development_groups": int(split.development_groups.nunique()),
        "audit_test_groups": int(split.audit_test_groups.nunique()),
        "data_version": data_version,
        "git_revision": git_revision,
        "profile": profile,
    }
    write_json(paths.protocol_path, protocol)

    evaluations: list[_CandidateEvaluation] = []
    failures: list[dict[str, str]] = []
    with _tracking_context(tracking_uri):
        experiment_id = _prepare_experiment(
            tracking_uri, experiment_name, paths.tracking_artifacts_dir
        )
        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=f"campaign__{profile}__{git_revision}",
            tags={
                "run_role": "campaign",
                "profile": profile,
                "git_revision": git_revision,
                "data_version": data_version,
            },
        ) as parent_run:
            mlflow.log_params(
                {
                    "candidate_count": len(catalog.candidates),
                    "n_splits": catalog.n_splits,
                    "random_seed": random_seed,
                    "selection_metric": "cv_pr_auc_mean",
                }
            )
            dataset = mlflow.data.from_pandas(  # type: ignore[attr-defined]
                validated.loc[:, (*FEATURE_COLUMNS, TARGET_COLUMN)],
                source="data/raw/online_shoppers_intention.csv",
                name="online-shoppers-intention",
                targets=TARGET_COLUMN,
            )
            mlflow.log_input(dataset, context="training")
            mlflow.log_artifact(str(paths.protocol_path))
            for spec in catalog.candidates:
                try:
                    with mlflow.start_run(
                        experiment_id=experiment_id,
                        run_name=spec.name,
                        nested=True,
                        tags={
                            "run_role": "candidate",
                            "family": spec.family,
                            "feature_set": spec.feature_set,
                            "git_revision": git_revision,
                            "data_version": data_version,
                        },
                    ) as candidate_run:
                        mlflow.log_params(_normalized_params(spec))
                        metrics, fold_metrics, threshold = _evaluate_candidate(
                            spec,
                            development,
                            split.development_groups,
                            n_splits=catalog.n_splits,
                            random_seed=random_seed,
                        )
                        mlflow.log_metrics(metrics)
                        mlflow.log_dict(
                            {"candidate": spec.name, "folds": list(fold_metrics)},
                            "fold_metrics.json",
                        )
                        evaluations.append(
                            _CandidateEvaluation(
                                spec=spec,
                                run_id=candidate_run.info.run_id,
                                threshold=threshold,
                                metrics=metrics,
                                fold_metrics=fold_metrics,
                            )
                        )
                except Exception as exc:
                    failures.append(
                        {
                            "candidate": spec.name,
                            "error_type": type(exc).__name__,
                            "error": str(exc)[:500],
                        }
                    )
            if not evaluations:
                raise RuntimeError("all experiment candidates failed")
            champion = max(
                evaluations,
                key=lambda result: (
                    result.metrics["cv_pr_auc_mean"],
                    result.metrics["oof_f1"],
                    -result.metrics["cv_pr_auc_std"],
                    result.spec.name,
                ),
            )
            comparison = {
                "selection_metric": "cv_pr_auc_mean",
                "champion": champion.spec.name,
                "parent_run_id": parent_run.info.run_id,
                "candidates": [
                    {
                        "name": result.spec.name,
                        "family": result.spec.family,
                        "feature_set": result.spec.feature_set,
                        "run_id": result.run_id,
                        "params": result.spec.params,
                        "metrics": result.metrics,
                    }
                    for result in sorted(
                        evaluations,
                        key=lambda item: item.metrics["cv_pr_auc_mean"],
                        reverse=True,
                    )
                ],
                "failures": failures,
            }
            write_json(paths.comparison_path, comparison)
            mlflow.log_artifact(str(paths.comparison_path))

            engineered, include_page_values = _feature_set_flags(champion.spec.feature_set)
            del engineered
            raw_columns = model_feature_columns(include_page_values=include_page_values)
            champion_pipeline = build_experiment_pipeline(champion.spec)
            champion_pipeline.fit(development.loc[:, raw_columns], development[TARGET_COLUMN])
            test_probabilities = champion_pipeline.predict_proba(
                split.audit_test.loc[:, raw_columns]
            )[:, 1]
            test_metrics = evaluate_probabilities(
                split.audit_test[TARGET_COLUMN], test_probabilities, champion.threshold
            )
            with mlflow.start_run(
                experiment_id=experiment_id,
                run_name=f"champion__{champion.spec.name}",
                nested=True,
                tags={
                    "run_role": "champion",
                    "source_candidate_run_id": champion.run_id,
                    "family": champion.spec.family,
                    "feature_set": champion.spec.feature_set,
                    "git_revision": git_revision,
                    "data_version": data_version,
                },
            ) as champion_run:
                champion_run_id = champion_run.info.run_id
                model_version = f"{git_revision}-{champion_run_id[:8]}"
                metrics_payload: dict[str, Any] = {
                    "champion": champion.spec.name,
                    "selection_metric": "cv_pr_auc_mean",
                    "source_candidate_run_id": champion.run_id,
                    "mlflow_run_id": champion_run_id,
                    "validation": champion.metrics,
                    "test": test_metrics,
                    "candidates": {result.spec.name: result.metrics for result in evaluations},
                    "failures": failures,
                }
                write_json(paths.metrics_path, metrics_payload)
                bundle = ModelBundle(
                    pipeline=champion_pipeline,
                    feature_names=raw_columns,
                    threshold=champion.threshold,
                    schema_version=ARTIFACT_SCHEMA_VERSION,
                    model_version=model_version,
                )
                metadata = write_artifact(
                    bundle,
                    paths.artifact_path,
                    paths.metadata_path,
                    {
                        "git_revision": git_revision,
                        "data_version": data_version,
                        "mlflow_run_id": champion_run_id,
                        "mlflow_experiment": experiment_name,
                        "selection_metric": "cv_pr_auc_mean",
                        "champion": champion.spec.name,
                        "family": champion.spec.family,
                        "feature_set": champion.spec.feature_set,
                        "include_page_values": include_page_values,
                        "baseline_rate": float(validated[TARGET_COLUMN].mean()),
                        "candidate_params": champion.spec.params,
                        "validation_metrics": champion.metrics,
                        "test_metrics": test_metrics,
                        "dataset": dataset_summary(validated),
                        "versions": {
                            "python": platform.python_version(),
                            "scikit_learn": sklearn.__version__,
                            "joblib": joblib.__version__,
                        },
                    },
                )
                write_json(paths.metadata_path, metadata)
                mlflow.log_params(_normalized_params(champion.spec))
                mlflow.log_param("source_candidate_run_id", champion.run_id)
                mlflow.log_metrics(
                    {
                        **{
                            f"validation_{key}": float(value)
                            for key, value in champion.metrics.items()
                        },
                        **{f"test_{key}": float(value) for key, value in test_metrics.items()},
                    }
                )
                mlflow.log_artifact(str(paths.artifact_path))
                mlflow.log_artifact(str(paths.metadata_path))
                mlflow.log_artifact(str(paths.metrics_path))
                _log_registered_model(
                    champion_pipeline,
                    development.loc[:, raw_columns].head(5),
                    registered_model_name=registered_model_name,
                    champion_run_id=champion_run_id,
                )

    return CampaignOutcome(
        champion_name=champion.spec.name,
        champion_run_id=champion_run_id,
        threshold=champion.threshold,
        validation_metrics={key: value for key, value in champion.metrics.items()},
        test_metrics=test_metrics,
    )
