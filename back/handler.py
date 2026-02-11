"""
AWS Lambda handler for FastAPI application.

This module provides the Lambda entry point using Mangum adapter.
"""

from mangum import Mangum

from app.main import app
from app.core.database import create_tables

# Lambda 콜드 스타트 시 누락된 테이블 자동 생성 (멱등성 보장)
create_tables()

# Lambda handler - lifespan="off" because Lambda doesn't support ASGI lifespan
handler = Mangum(app, lifespan="off")
