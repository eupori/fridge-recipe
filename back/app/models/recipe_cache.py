"""Recipe cache model for avoiding redundant LLM + image API calls"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String

from app.core.database import Base


class RecipeCache(Base):
    """레시피 캐시 DB 모델 — 동일 재료 조합에 대한 LLM 결과 재사용"""

    __tablename__ = "recipe_cache"

    cache_key = Column(String(64), primary_key=True)  # SHA256 hex digest
    recommendation_data = Column(JSON, nullable=False)  # RecommendationResponse dict
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    hit_count = Column(Integer, nullable=False, default=0)
