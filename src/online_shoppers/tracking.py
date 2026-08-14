"""Small MLflow boundary used by the training notebook."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import mlflow
from mlflow.entities import Run


@contextmanager
def tracked_run(
    *,
    tracking_uri: str,
    experiment_name: str,
    run_name: str,
    params: Mapping[str, Any],
) -> Iterator[Run]:
    """Create a run, log normalized parameters, and restore global MLflow state."""

    previous_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(tracking_uri)
    try:
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=run_name) as run:
            if params:
                mlflow.log_params({key: str(value) for key, value in params.items()})
            yield run
    finally:
        mlflow.set_tracking_uri(previous_uri)
