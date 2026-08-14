from pathlib import Path

import numpy as np
import pandas as pd
from mlflow import MlflowClient

from online_shoppers.artifacts import load_artifact
from online_shoppers.data import FEATURE_COLUMNS, TARGET_COLUMN
from online_shoppers.training import train_champion


def separable_dataset(rows: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(10)
    target = np.array([False, True] * (rows // 2))
    return pd.DataFrame(
        {
            "Administrative": rng.integers(0, 4, rows),
            "Administrative_Duration": rng.uniform(0, 100, rows),
            "Informational": rng.integers(0, 3, rows),
            "Informational_Duration": rng.uniform(0, 50, rows),
            "ProductRelated": rng.integers(1, 20, rows),
            "ProductRelated_Duration": rng.uniform(1, 500, rows),
            "BounceRates": np.where(target, 0.01, 0.15),
            "ExitRates": np.where(target, 0.02, 0.18),
            "PageValues": np.where(target, 30.0, 0.0),
            "SpecialDay": rng.choice([0.0, 0.2], rows),
            "Month": rng.choice(["Feb", "Nov"], rows),
            "OperatingSystems": rng.choice([1, 2], rows),
            "Browser": rng.choice([1, 2], rows),
            "Region": rng.choice([1, 2], rows),
            "TrafficType": rng.choice([1, 2], rows),
            "VisitorType": rng.choice(["Returning_Visitor", "New_Visitor"], rows),
            "Weekend": rng.choice([False, True], rows),
            TARGET_COLUMN: target,
        }
    )


def test_train_champion_tracks_candidates_and_writes_loadable_artifact(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    artifact_path = tmp_path / "champion.joblib"
    metadata_path = tmp_path / "model_metadata.json"
    metrics_path = tmp_path / "model_metrics.json"

    outcome = train_champion(
        separable_dataset(),
        artifact_path=artifact_path,
        metadata_path=metadata_path,
        metrics_path=metrics_path,
        tracking_uri=tracking_uri,
        experiment_name="training-integration",
        random_seed=42,
        forest_estimators=10,
        git_revision="test-revision",
    )

    bundle, metadata = load_artifact(artifact_path, metadata_path)
    probabilities = bundle.pipeline.predict_proba(separable_dataset().loc[:, bundle.feature_names])[
        :, 1
    ]
    experiment = MlflowClient(tracking_uri=tracking_uri).get_experiment_by_name(
        "training-integration"
    )
    assert experiment is not None
    runs = MlflowClient(tracking_uri=tracking_uri).search_runs([experiment.experiment_id])

    assert outcome.champion_name in {"logistic_regression", "random_forest"}
    assert outcome.test_metrics["f1"] >= 0.8
    assert metadata["git_revision"] == "test-revision"
    assert metadata["selection_metric"] == "f1"
    assert metrics_path.exists()
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    assert len(runs) == 7

    run_names = {run.data.tags.get("mlflow.runName") for run in runs}

    assert "logistic_regression__with_page_values" in run_names
    assert "logistic_regression__without_page_values" in run_names
    assert "random_forest__with_page_values" in run_names
    assert "random_forest__without_page_values" in run_names
    assert "dummy__with_page_values" in run_names
    assert "dummy__without_page_values" in run_names
    assert "champion" in run_names

    assert set(bundle.feature_names).issubset(FEATURE_COLUMNS)
