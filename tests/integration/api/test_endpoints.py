import json
import logging
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from online_shoppers.api.main import create_app
from online_shoppers.api.service import PredictionService
from online_shoppers.artifacts import ARTIFACT_SCHEMA_VERSION, ModelBundle
from online_shoppers.data import FEATURE_COLUMNS
from tests.factories import valid_prediction_payload


class FixedPipeline:
    def predict_proba(self, frame: object) -> np.ndarray:
        return np.array([[0.25, 0.75]])


def service() -> PredictionService:
    return PredictionService(
        bundle=ModelBundle(
            pipeline=FixedPipeline(),
            feature_names=FEATURE_COLUMNS,
            threshold=0.5,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            model_version="api-test-v1",
        ),
        metadata={
            "champion": "fixed",
            "validation_metrics": {"f1": 0.7},
            "test_metrics": {"f1": 0.68},
        },
    )


def test_health_metadata_and_prediction_contract() -> None:
    with TestClient(create_app(service=service())) as client:
        health = client.get("/health")
        metadata = client.get("/v1/model/metadata")
        prediction = client.post("/v1/predict", json=valid_prediction_payload())

    assert health.json() == {"status": "ok", "model_version": "api-test-v1"}
    assert metadata.status_code == 200
    assert metadata.json()["model_version"] == "api-test-v1"
    assert prediction.status_code == 200
    assert prediction.json() == {
        "will_purchase": True,
        "purchase_probability": 0.75,
        "threshold": 0.5,
        "model_version": "api-test-v1",
    }


def test_prediction_at_threshold_is_classified_as_purchase() -> None:
    class ThresholdPipeline:
        def predict_proba(self, frame: object) -> np.ndarray:
            return np.array([[0.5, 0.5]])

    threshold_service = PredictionService(
        bundle=ModelBundle(
            pipeline=ThresholdPipeline(),
            feature_names=FEATURE_COLUMNS,
            threshold=0.5,
            schema_version=ARTIFACT_SCHEMA_VERSION,
            model_version="api-threshold-test-v1",
        ),
        metadata={"champion": "threshold-test"},
    )

    with TestClient(create_app(service=threshold_service)) as client:
        response = client.post("/v1/predict", json=valid_prediction_payload())

    assert response.status_code == 200
    assert response.json()["purchase_probability"] == 0.5
    assert response.json()["threshold"] == 0.5
    assert response.json()["will_purchase"] is True


def test_prediction_returns_422_without_leaking_traceback() -> None:
    invalid = valid_prediction_payload()
    invalid["BounceRates"] = 5

    with TestClient(create_app(service=service())) as client:
        response = client.post("/v1/predict", json=invalid)

    assert response.status_code == 422
    assert "traceback" not in response.text.lower()


def test_missing_artifact_degrades_health_and_returns_503(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "missing.joblib"))  # type: ignore[attr-defined]
    monkeypatch.setenv("MODEL_METADATA_PATH", str(tmp_path / "missing.json"))  # type: ignore[attr-defined]

    with TestClient(create_app()) as client:
        health = client.get("/health")
        prediction = client.post("/v1/predict", json=valid_prediction_payload())

    assert health.json() == {"status": "degraded", "model_version": None}
    assert prediction.status_code == 503
    assert prediction.json() == {"detail": "model is unavailable"}


def test_cors_is_restricted_to_configured_origin(monkeypatch: object) -> None:
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://example.vercel.app")  # type: ignore[attr-defined]
    with TestClient(create_app(service=service())) as client:
        response = client.options(
            "/v1/predict",
            headers={
                "Origin": "https://example.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.headers["access-control-allow-origin"] == "https://example.vercel.app"


def test_request_log_contains_operational_context(caplog: pytest.LogCaptureFixture) -> None:
    with (
        caplog.at_level(logging.INFO, logger="online_shoppers.api.main"),
        TestClient(create_app(service=service())) as client,
    ):
        response = client.get("/health", headers={"x-request-id": "request-123"})

    assert response.status_code == 200
    payload = json.loads(caplog.records[-1].message)
    assert payload["request_id"] == "request-123"
    assert payload["route"] == "/health"
    assert payload["status"] == 200
    assert payload["model_version"] == "api-test-v1"
    assert payload["duration_ms"] >= 0


def test_openapi_contract_matches_versioned_snapshot() -> None:
    snapshot = json.loads(Path("contracts/openapi.json").read_text())

    assert create_app(service=service()).openapi() == snapshot
