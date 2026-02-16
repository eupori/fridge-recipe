"""
Public stats endpoint

사용 통계 공개 API (레시피 수, 사용자 수)
인메모리 캐싱으로 DB 쿼리 부하 감소 (60초 TTL)
"""

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.recommendation import RecommendationRecord
from app.models.user import User

router = APIRouter()

_stats_cache: dict = {"data": None, "expires_at": 0}
CACHE_TTL = 60  # seconds


@router.get(
    "",
    summary="사용 통계",
    description="서비스 사용 통계를 반환합니다.",
)
def get_stats(db: Session = Depends(get_db)):
    now = time.time()
    if _stats_cache["data"] and now < _stats_cache["expires_at"]:
        return _stats_cache["data"]

    total_recs = db.query(RecommendationRecord).count()
    total_users = db.query(User).count()
    data = {
        "total_recipes_generated": total_recs * 3,
        "total_users": total_users,
    }

    _stats_cache["data"] = data
    _stats_cache["expires_at"] = now + CACHE_TTL
    return data
