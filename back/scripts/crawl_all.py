"""통합 크롤링 실행 스크립트

사용법:
    cd back && PYTHONPATH=. python scripts/crawl_all.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func

from app.core.database import SessionLocal, create_tables
from app.models.reference_recipe import ReferenceRecipe

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def print_summary() -> None:
    """DB에 저장된 레퍼런스 레시피 요약 출력"""
    db = SessionLocal()
    total = db.query(ReferenceRecipe).count()

    print(f"\n{'=' * 50}")
    print(f"=== 결과 요약 ===")
    print(f"총 레퍼런스 레시피: {total}개")

    print("\n소스별:")
    for source, cnt in (
        db.query(ReferenceRecipe.source, func.count())
        .group_by(ReferenceRecipe.source)
        .all()
    ):
        print(f"  {source}: {cnt}개")

    print("\n카테고리별:")
    for cat, cnt in (
        db.query(ReferenceRecipe.category, func.count())
        .group_by(ReferenceRecipe.category)
        .all()
    ):
        print(f"  {cat}: {cnt}개")

    print(f"{'=' * 50}\n")
    db.close()


def main() -> None:
    print("=== 레시피 크롤링 시작 ===\n")

    create_tables()

    # 1. 만개의레시피
    print("[1/2] 만개의레시피 크롤링...")
    try:
        from scripts.crawl_10000recipe import crawl_10000recipe

        count_10000 = crawl_10000recipe()
        print(f"  → {count_10000}개 저장\n")
    except Exception as e:
        logger.error(f"만개의레시피 크롤링 실패: {e}")
        count_10000 = 0

    # 2. YouTube 셰프
    print("[2/2] YouTube 셰프 채널 크롤링...")
    try:
        from scripts.crawl_youtube_chefs import crawl_youtube_chefs

        count_yt = crawl_youtube_chefs()
        print(f"  → {count_yt}개 저장\n")
    except Exception as e:
        logger.error(f"YouTube 셰프 크롤링 실패: {e}")
        count_yt = 0

    print_summary()


if __name__ == "__main__":
    main()
