#!/usr/bin/env python3
"""레퍼런스 레시피 JSON 임포트 스크립트

사용법:
    cd back
    PYTHONPATH=. python scripts/import_recipes.py data/recipes.json
    PYTHONPATH=. python scripts/import_recipes.py data/*.json
    PYTHONPATH=. python scripts/import_recipes.py data/recipes.json --dry-run
    PYTHONPATH=. python scripts/import_recipes.py data/recipes.json --stats

입력 JSON 포맷 (배열 또는 JSONL):

    [배열 형식] recipes.json:
    [
      {
        "title": "김치찌개",
        "category": "국물",
        "key_ingredients": ["김치", "돼지고기", "두부"],
        "all_ingredients": ["김치 200g", "돼지고기 150g", "두부 1/2모"],
        "steps": ["김치를 볶는다", "물을 붓고 끓인다"],
        "technique": "잘 익은 김치를 센불에 볶아 신맛 날리기",
        "time_min": 15,
        "servings": 2,
        "source": "만개의레시피",
        "source_url": "https://www.10000recipe.com/recipe/123456",
        "view_count": 50000,
        "rating": 45
      }
    ]

    [JSONL 형식] recipes.jsonl:
    {"title": "김치찌개", "category": "국물", ...}
    {"title": "된장찌개", "category": "국물", ...}

필수 필드: title, category, key_ingredients, all_ingredients, steps, source, source_url
선택 필드: technique, time_min, servings, view_count, rating
"""
from __future__ import annotations

import argparse
import json
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

REQUIRED_FIELDS = {"title", "category", "key_ingredients", "all_ingredients", "steps", "source", "source_url"}
VALID_CATEGORIES = {"밥", "국물", "반찬단품", "면분식", "양식", "아시안", "퓨전", "안주", "간식"}


def validate_recipe(data: dict, index: int) -> list[str]:
    """레시피 데이터 검증. 오류 목록 반환 (빈 리스트 = 통과)."""
    errors = []
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        errors.append(f"#{index}: 필수 필드 누락: {missing}")
        return errors

    if not data["title"] or not data["title"].strip():
        errors.append(f"#{index}: title이 비어있음")
    if not isinstance(data["key_ingredients"], list) or not data["key_ingredients"]:
        errors.append(f"#{index}: key_ingredients가 비어있거나 배열이 아님")
    if not isinstance(data["all_ingredients"], list) or not data["all_ingredients"]:
        errors.append(f"#{index}: all_ingredients가 비어있거나 배열이 아님")
    if not isinstance(data["steps"], list) or not data["steps"]:
        errors.append(f"#{index}: steps가 비어있거나 배열이 아님")
    if not data["source_url"] or not data["source_url"].strip():
        errors.append(f"#{index}: source_url이 비어있음")
    if data["category"] not in VALID_CATEGORIES:
        errors.append(
            f"#{index}: category '{data['category']}' 미지원 "
            f"(허용: {VALID_CATEGORIES})"
        )

    return errors


def load_recipes(file_path: Path) -> list[dict]:
    """JSON 또는 JSONL 파일에서 레시피 로드"""
    text = file_path.read_text(encoding="utf-8").strip()

    # JSONL 형식 감지 (첫 줄이 { 로 시작하고 전체가 [ 로 시작하지 않으면)
    if text.startswith("{"):
        recipes = []
        for line_num, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                recipes.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"  JSONL 파싱 실패 (줄 {line_num}): {e}")
        return recipes

    # 일반 JSON 배열
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def import_recipes(
    file_paths: list[Path], dry_run: bool = False
) -> tuple[int, int, int]:
    """레시피 임포트. (성공, 중복, 오류) 카운트 반환."""
    create_tables()
    db = SessionLocal()

    total_ok, total_dup, total_err = 0, 0, 0

    for fp in file_paths:
        if not fp.exists():
            logger.error(f"파일 없음: {fp}")
            total_err += 1
            continue

        logger.info(f"파일 로드: {fp}")
        try:
            recipes = load_recipes(fp)
        except Exception as e:
            logger.error(f"파일 파싱 실패: {fp}: {e}")
            total_err += 1
            continue

        logger.info(f"  {len(recipes)}개 레시피 발견")

        for i, recipe in enumerate(recipes):
            # 검증
            errors = validate_recipe(recipe, i)
            if errors:
                for err in errors:
                    logger.warning(f"  검증 실패: {err}")
                total_err += 1
                continue

            # 중복 체크
            exists = (
                db.query(ReferenceRecipe)
                .filter(ReferenceRecipe.source_url == recipe["source_url"])
                .first()
            )
            if exists:
                total_dup += 1
                continue

            if dry_run:
                total_ok += 1
                continue

            # 저장
            record = ReferenceRecipe(
                title=recipe["title"].strip(),
                category=recipe["category"],
                key_ingredients=recipe["key_ingredients"],
                all_ingredients=recipe["all_ingredients"],
                steps=recipe["steps"],
                technique=recipe.get("technique"),
                time_min=recipe.get("time_min"),
                servings=recipe.get("servings"),
                source=recipe["source"],
                source_url=recipe["source_url"],
                view_count=recipe.get("view_count", 0),
                rating=recipe.get("rating"),
            )
            db.add(record)
            try:
                db.commit()
                total_ok += 1
            except Exception as e:
                db.rollback()
                logger.warning(f"  저장 실패 #{i}: {e}")
                total_err += 1

        if total_ok > 0 and total_ok % 500 == 0:
            logger.info(f"  진행: {total_ok}개 저장")

    db.close()
    return total_ok, total_dup, total_err


def print_stats() -> None:
    """DB 통계 출력"""
    create_tables()
    db = SessionLocal()
    total = db.query(ReferenceRecipe).count()

    print(f"\n총 레퍼런스 레시피: {total:,}개\n")

    print("카테고리별:")
    for cat, cnt in (
        db.query(ReferenceRecipe.category, func.count())
        .group_by(ReferenceRecipe.category)
        .order_by(func.count().desc())
        .all()
    ):
        print(f"  {cat:<8} {cnt:>6,}개")

    print("\n소스별:")
    for source, cnt in (
        db.query(ReferenceRecipe.source, func.count())
        .group_by(ReferenceRecipe.source)
        .order_by(func.count().desc())
        .all()
    ):
        print(f"  {source:<20} {cnt:>6,}개")

    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="레퍼런스 레시피 JSON → DB 임포트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files", nargs="*", type=Path,
        help="임포트할 JSON/JSONL 파일 (여러 개 가능)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 저장 없이 검증만",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="현재 DB 통계 출력",
    )

    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    if not args.files:
        parser.error("임포트할 파일을 지정하세요 (예: data/recipes.json)")

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}레시피 임포트 시작: {len(args.files)}개 파일\n")

    ok, dup, err = import_recipes(args.files, dry_run=args.dry_run)

    print(f"\n{'=' * 40}")
    print(f"  {prefix}임포트 결과")
    print(f"  성공: {ok:,}개")
    print(f"  중복 스킵: {dup:,}개")
    print(f"  오류: {err:,}개")
    print(f"{'=' * 40}\n")

    if not args.dry_run and ok > 0:
        print_stats()


if __name__ == "__main__":
    main()
