from fastapi import APIRouter, HTTPException

from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
)
from app.services.recommendation_service import create_recommendation, get_recommendation

router = APIRouter()


@router.post("", response_model=RecommendationResponse)
def post_recommendations(payload: RecommendationCreate):
    try:
        return create_recommendation(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendations(recommendation_id: str):
    rec = get_recommendation(recommendation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="not_found")
    return rec
