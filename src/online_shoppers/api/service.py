"""Inference service isolated from HTTP and Lambda details."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from online_shoppers.api.schemas import MetadataResponse, PredictionResponse, SessionFeatures
from online_shoppers.artifacts import ModelBundle, load_artifact


class PredictionService:
    """Own the verified model bundle and its public operations."""

    def __init__(self, *, bundle: ModelBundle, metadata: Mapping[str, Any]) -> None:
        self.bundle = bundle
        self.metadata = dict(metadata)

    @classmethod
    def from_environment(cls) -> PredictionService:
        artifact_path = Path(os.getenv("MODEL_PATH", "models/champion.joblib"))
        metadata_path = Path(os.getenv("MODEL_METADATA_PATH", "models/model_metadata.json"))
        bundle, metadata = load_artifact(artifact_path, metadata_path)
        return cls(bundle=bundle, metadata=metadata)

    def predict(self, session: SessionFeatures) -> PredictionResponse:
        payload = session.model_dump(by_alias=True)
        frame = pd.DataFrame([{name: payload[name] for name in self.bundle.feature_names}])
        probability = float(self.bundle.pipeline.predict_proba(frame)[0, 1])
        return PredictionResponse(
            will_purchase=probability >= self.bundle.threshold,
            purchase_probability=probability,
            threshold=self.bundle.threshold,
            model_version=self.bundle.model_version,
        )

    def public_metadata(self) -> MetadataResponse:
        return MetadataResponse(
            model_version=self.bundle.model_version,
            feature_names=list(self.bundle.feature_names),
            threshold=self.bundle.threshold,
            champion=self.metadata.get("champion"),
            validation_metrics=dict(self.metadata.get("validation_metrics", {})),
            test_metrics=dict(self.metadata.get("test_metrics", {})),
        )
