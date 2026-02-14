from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.favorites import router as favorites_router
from app.api.v1.endpoints.images import router as images_router
from app.api.v1.endpoints.recommendations import router as recommendations_router
from app.api.v1.endpoints.search_histories import router as search_histories_router
from app.api.v1.endpoints.stats import router as stats_router

api_router = APIRouter()
api_router.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(favorites_router, prefix="/favorites", tags=["favorites"])
api_router.include_router(
    search_histories_router, prefix="/search-histories", tags=["search-histories"]
)
api_router.include_router(images_router, prefix="/images", tags=["images"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
