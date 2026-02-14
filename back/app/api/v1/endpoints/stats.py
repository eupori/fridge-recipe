"""
Public stats endpoint

사용 통계 공개 API (레시피 수, 사용자 수)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recommendation import RecommendationRecord
from app.models.user import User

router = APIRouter()


@router.get(
    "",
    summary="사용 통계",
    description="서비스 사용 통계를 반환합니다.",
)
def get_stats(db: Session = Depends(get_db)):
    total_recs = db.query(RecommendationRecord).count()
    total_users = db.query(User).count()
    return {
        "total_recipes_generated": total_recs * 3,
        "total_users": total_users,
    }
