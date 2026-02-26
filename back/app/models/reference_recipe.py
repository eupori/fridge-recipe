"""레퍼런스 레시피 DB 모델 — 크롤링된 레시피 저장"""
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from app.core.database import Base


class ReferenceRecipe(Base):
    """크롤링된 레퍼런스 레시피"""

    __tablename__ = "reference_recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 레시피 상세
    title = Column(String(100), nullable=False, index=True)
    category = Column(String(20), nullable=False, index=True)
    key_ingredients = Column(JSON, nullable=False)
    all_ingredients = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    technique = Column(Text, nullable=True)
    time_min = Column(Integer, nullable=True)
    servings = Column(Integer, nullable=True)

    # 원본 백업 (리라이팅 전 steps)
    original_steps = Column(JSON, nullable=True)

    # 메타
    source = Column(String(50), nullable=False, index=True)
    source_url = Column(String(500), nullable=False, unique=True)
    view_count = Column(Integer, default=0)
    rating = Column(Integer, nullable=True)

    # 타임스탬프
    crawled_at = Column(DateTime, default=func.now())
