from __future__ import annotations

from pathlib import Path

from mlflow import MlflowClient

from online_shoppers.artifacts import load_artifact
from online_shoppers.experimentation import CampaignPaths, run_experiment_campaign
from tests.unit.test_modeling import synthetic_dataset


def test_smoke_campaign_tracks_every_candidate_and_writes_champion(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    experiment_name = "campaign-integration"
    paths = CampaignPaths(
        artifact_path=tmp_path / "champion.joblib",
        metadata_path=tmp_path / "model_metadata.json",
        metrics_path=tmp_path / "model_metrics.json",
        comparison_path=tmp_path / "final_model_comparison.json",
        protocol_path=tmp_path / "protocol_manifest.json",
        tracking_artifacts_dir=tmp_path / "mlflow-artifacts",
    )

    outcome = run_experiment_campaign(
        synthetic_dataset(120),
        tracking_uri=tracking_uri,
        paths=paths,
        profile="smoke",
        experiment_name=experiment_name,
        registered_model_name=None,
        git_revision="test-sha",
        data_version="test-dvc-hash",
        random_seed=42,
    )

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    assert experiment is not None
    runs = client.search_runs([experiment.experiment_id])
    candidate_runs = [run for run in runs if run.data.tags.get("run_role") == "candidate"]
    champion_runs = [run for run in runs if run.data.tags.get("run_role") == "champion"]
    bundle, metadata = load_artifact(paths.artifact_path, paths.metadata_path)

    assert len(candidate_runs) == 2
    assert len(champion_runs) == 1
    assert outcome.champion_run_id == champion_runs[0].info.run_id
    assert all("cv_pr_auc_mean" in run.data.metrics for run in candidate_runs)
    assert all("oof_f1" in run.data.metrics for run in candidate_runs)
    assert "test_pr_auc" in champion_runs[0].data.metrics
    assert metadata["mlflow_run_id"] == outcome.champion_run_id
    assert metadata["data_version"] == "test-dvc-hash"
    assert bundle.model_version.startswith("test-sha-")
    assert paths.comparison_path.exists()
    assert paths.protocol_path.exists()
