"""FastAPI application factory."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from online_shoppers.api.schemas import (
    HealthResponse,
    MetadataResponse,
    PredictionResponse,
    SessionFeatures,
)
from online_shoppers.api.service import PredictionService

LOGGER = logging.getLogger(__name__)


def create_app(*, service: PredictionService | None = None) -> FastAPI:
    """Create an app with an injectable service for deterministic tests."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.prediction_service = service
        app.state.load_error = None
        if service is None:
            try:
                app.state.prediction_service = PredictionService.from_environment()
            except Exception as exc:  # startup must expose degraded health, not crash Lambda
                LOGGER.error("model_load_failed", extra={"error_type": type(exc).__name__})
                app.state.load_error = exc
        yield

    application = FastAPI(
        title="Online Shoppers Purchase Intention API",
        version="1.0.0",
        lifespan=lifespan,
    )
    allowed_origin = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[allowed_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @application.middleware("http")
    async def log_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            current_service = getattr(request.app.state, "prediction_service", None)
            model_version = (
                current_service.bundle.model_version
                if isinstance(current_service, PredictionService)
                else None
            )
            LOGGER.info(
                json.dumps(
                    {
                        "duration_ms": round((perf_counter() - started_at) * 1000, 3),
                        "method": request.method,
                        "model_version": model_version,
                        "request_id": request.headers.get("x-request-id", "unknown"),
                        "route": request.url.path,
                        "status": status_code,
                    },
                    sort_keys=True,
                )
            )

    def get_service(request: Request) -> PredictionService:
        current_service = request.app.state.prediction_service
        if not isinstance(current_service, PredictionService):
            raise HTTPException(status_code=503, detail="model is unavailable")
        return current_service

    @application.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        current_service = request.app.state.prediction_service
        if isinstance(current_service, PredictionService):
            return HealthResponse(status="ok", model_version=current_service.bundle.model_version)
        return HealthResponse(status="degraded", model_version=None)

    @application.get("/v1/model/metadata", response_model=MetadataResponse)
    def metadata(request: Request) -> MetadataResponse:
        return get_service(request).public_metadata()

    @application.post("/v1/predict", response_model=PredictionResponse)
    def predict(request: Request, session: SessionFeatures) -> PredictionResponse:
        return get_service(request).predict(session)

    return application


app = create_app()
