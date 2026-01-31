from fastapi import APIRouter

from app.api.v1.endpoints.recommendations import router as recommendations_router

api_router = APIRouter()
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
