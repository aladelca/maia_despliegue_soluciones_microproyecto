"""Controlled serialization and integrity checks for the champion model."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

ARTIFACT_SCHEMA_VERSION = "1"


class ArtifactValidationError(ValueError):
    """Raised when a local model artifact fails integrity or schema checks."""


@dataclass
class ModelBundle:
    """Everything needed to produce a prediction without notebook state."""

    pipeline: Any
    feature_names: tuple[str, ...]
    threshold: float
    schema_version: str
    model_version: str


def sha256_file(path: str | Path) -> str:
    """Calculate a streaming SHA-256 digest."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_artifact(
    bundle: ModelBundle,
    artifact_path: str | Path,
    metadata_path: str | Path,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically write a controlled bundle and metadata containing its checksum."""

    artifact = Path(artifact_path)
    metadata_file = Path(metadata_path)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    metadata_file.parent.mkdir(parents=True, exist_ok=True)

    temporary_artifact = artifact.with_suffix(f"{artifact.suffix}.tmp")
    joblib.dump(bundle, temporary_artifact)
    os.replace(temporary_artifact, artifact)

    stored_metadata: dict[str, Any] = dict(metadata)
    stored_metadata.update(
        {
            "sha256": sha256_file(artifact),
            "schema_version": bundle.schema_version,
            "model_version": bundle.model_version,
            "feature_names": list(bundle.feature_names),
            "threshold": bundle.threshold,
        }
    )
    temporary_metadata = metadata_file.with_suffix(f"{metadata_file.suffix}.tmp")
    temporary_metadata.write_text(
        json.dumps(stored_metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_metadata, metadata_file)
    return stored_metadata


def load_artifact(
    artifact_path: str | Path, metadata_path: str | Path
) -> tuple[ModelBundle, dict[str, Any]]:
    """Verify and load an artifact produced by this repository.

    Joblib uses pickle internally. Callers must never pass a user-controlled path.
    """

    artifact = Path(artifact_path)
    metadata_file = Path(metadata_path)
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError("model metadata cannot be read") from exc

    expected_checksum = metadata.get("sha256")
    if not isinstance(expected_checksum, str) or sha256_file(artifact) != expected_checksum:
        raise ArtifactValidationError("model artifact checksum does not match metadata")

    loaded = joblib.load(artifact)
    if not isinstance(loaded, ModelBundle):
        raise ArtifactValidationError("model artifact does not contain a ModelBundle")
    if loaded.schema_version != ARTIFACT_SCHEMA_VERSION:
        raise ArtifactValidationError(
            f"unsupported model artifact schema: {loaded.schema_version!r}"
        )
    if not 0 <= loaded.threshold <= 1:
        raise ArtifactValidationError("model threshold must be between 0 and 1")
    if tuple(metadata.get("feature_names", ())) != loaded.feature_names:
        raise ArtifactValidationError("model feature schema does not match metadata")
    return loaded, metadata
