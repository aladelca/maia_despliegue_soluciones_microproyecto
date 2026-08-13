import json
from pathlib import Path

import pytest

from online_shoppers.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactValidationError,
    ModelBundle,
    load_artifact,
    write_artifact,
)


def bundle() -> ModelBundle:
    return ModelBundle(
        pipeline={"kind": "test-pipeline"},
        feature_names=("a", "b"),
        threshold=0.42,
        schema_version=ARTIFACT_SCHEMA_VERSION,
        model_version="test-v1",
    )


def test_artifact_round_trip_writes_hash_to_metadata(tmp_path: Path) -> None:
    artifact_path = tmp_path / "champion.joblib"
    metadata_path = tmp_path / "model_metadata.json"

    metadata = write_artifact(bundle(), artifact_path, metadata_path, {"f1": 0.8})
    loaded, loaded_metadata = load_artifact(artifact_path, metadata_path)

    assert loaded == bundle()
    assert loaded_metadata == metadata
    assert len(metadata["sha256"]) == 64
    assert json.loads(metadata_path.read_text())["model_version"] == "test-v1"


def test_artifact_loader_rejects_modified_binary(tmp_path: Path) -> None:
    artifact_path = tmp_path / "champion.joblib"
    metadata_path = tmp_path / "model_metadata.json"
    write_artifact(bundle(), artifact_path, metadata_path, {})
    artifact_path.write_bytes(artifact_path.read_bytes() + b"tampered")

    with pytest.raises(ArtifactValidationError, match="checksum"):
        load_artifact(artifact_path, metadata_path)


def test_artifact_loader_rejects_incompatible_schema(tmp_path: Path) -> None:
    artifact_path = tmp_path / "champion.joblib"
    metadata_path = tmp_path / "model_metadata.json"
    incompatible = bundle()
    incompatible.schema_version = "999"
    write_artifact(incompatible, artifact_path, metadata_path, {})

    with pytest.raises(ArtifactValidationError, match="schema"):
        load_artifact(artifact_path, metadata_path)
