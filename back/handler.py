"""
AWS Lambda handler for FastAPI application.

This module provides the Lambda entry point using Mangum adapter.
"""
from mangum import Mangum
from app.main import app

# Lambda handler - lifespan="off" because Lambda doesn't support ASGI lifespan
handler = Mangum(app, lifespan="off")
