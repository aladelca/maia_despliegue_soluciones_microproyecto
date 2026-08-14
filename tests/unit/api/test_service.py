import numpy as np

from online_shoppers.api.schemas import SessionFeatures
from online_shoppers.api.service import PredictionService
from online_shoppers.artifacts import ARTIFACT_SCHEMA_VERSION, ModelBundle
from online_shoppers.data import FEATURE_COLUMNS
from tests.factories import valid_prediction_payload


class RecordingPipeline:
    def __init__(self, probability: float) -> None:
        self.probability = probability
        self.seen_columns: list[str] = []

    def predict_proba(self, frame: object) -> np.ndarray:
        self.seen_columns = list(frame.columns)  # type: ignore[attr-defined]
        return np.array([[1 - self.probability, self.probability]])


def test_prediction_service_orders_features_and_applies_threshold() -> None:
    pipeline = RecordingPipeline(0.73)
    bundle = ModelBundle(
        pipeline=pipeline,
        feature_names=FEATURE_COLUMNS,
        threshold=0.60,
        schema_version=ARTIFACT_SCHEMA_VERSION,
        model_version="test-v1",
    )
    service = PredictionService(bundle=bundle, metadata={"champion": "forest"})

    response = service.predict(SessionFeatures.model_validate(valid_prediction_payload()))

    assert pipeline.seen_columns == list(FEATURE_COLUMNS)
    assert response.will_purchase is True
    assert response.purchase_probability == 0.73
    assert response.threshold == 0.60
    assert response.model_version == "test-v1"


def test_prediction_service_supports_bundle_without_page_values() -> None:
    pipeline = RecordingPipeline(0.2)
    feature_names = tuple(column for column in FEATURE_COLUMNS if column != "PageValues")
    service = PredictionService(
        bundle=ModelBundle(
            pipeline=pipeline,
            feature_names=feature_names,
            threshold=0.5,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            model_version="without-page-values",
        ),
        metadata={},
    )

    response = service.predict(SessionFeatures.model_validate(valid_prediction_payload()))

    assert "PageValues" not in pipeline.seen_columns
    assert response.will_purchase is False
