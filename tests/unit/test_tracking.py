from pathlib import Path

import mlflow
import pytest
from mlflow import MlflowClient

from online_shoppers.tracking import tracked_run


def test_tracked_run_records_parameters_metrics_and_artifact(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    artifact = tmp_path / "metrics.json"
    artifact.write_text('{"f1": 0.8}')

    with tracked_run(
        tracking_uri=tracking_uri,
        experiment_name="unit-tests",
        run_name="logistic",
        params={"model": "logistic", "with_page_values": True},
    ) as run:
        mlflow.log_metric("f1", 0.8)
        mlflow.log_artifact(str(artifact))
        run_id = run.info.run_id

    client = MlflowClient(tracking_uri=tracking_uri)
    stored = client.get_run(run_id)
    artifacts = client.list_artifacts(run_id)
    assert stored.info.status == "FINISHED"
    assert stored.data.params["model"] == "logistic"
    assert stored.data.metrics["f1"] == pytest.approx(0.8)
    assert [item.path for item in artifacts] == ["metrics.json"]


def test_tracked_run_marks_failed_run_and_restores_tracking_uri(tmp_path: Path) -> None:
    original_uri = mlflow.get_tracking_uri()
    tracking_uri = f"sqlite:///{tmp_path / 'failed-mlflow.db'}"
    run_id = ""

    with (
        pytest.raises(RuntimeError, match="expected failure"),
        tracked_run(
            tracking_uri=tracking_uri,
            experiment_name="unit-tests",
            run_name="failure",
            params={},
        ) as run,
    ):
        run_id = run.info.run_id
        raise RuntimeError("expected failure")

    assert mlflow.get_tracking_uri() == original_uri
    assert MlflowClient(tracking_uri=tracking_uri).get_run(run_id).info.status == "FAILED"
