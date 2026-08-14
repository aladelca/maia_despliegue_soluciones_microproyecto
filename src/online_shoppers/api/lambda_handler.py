"""AWS Lambda entry point for API Gateway HTTP API payload version 2."""

from mangum import Mangum

from online_shoppers.api.main import app

handler = Mangum(app, lifespan="auto")
