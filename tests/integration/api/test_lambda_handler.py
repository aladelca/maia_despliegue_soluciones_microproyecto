import json
from typing import Any, cast

from online_shoppers.api.lambda_handler import handler


def test_lambda_handler_maps_http_api_v2_health_request() -> None:
    event = {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "example.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "test-request",
            "routeKey": "GET /health",
            "stage": "$default",
            "time": "12/Aug/2026:00:00:00 +0000",
            "timeEpoch": 0,
        },
        "isBase64Encoded": False,
    }

    response = handler(event, cast(Any, {}))

    assert response["statusCode"] == 200
    payload = json.loads(response["body"])
    assert payload["status"] in {"ok", "degraded"}
    assert "model_version" in payload
