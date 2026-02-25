"""크롤러 공통 유틸리티 — DB 세션, 중복 체크, 재료 추출"""
from __future__ import annotations

import logging
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, create_tables
from app.models.reference_recipe import ReferenceRecipe

logger = logging.getLogger(__name__)

# 만개의레시피 카테고리 매핑
CATEGORY_MAP = {
    52: "밥",
    53: "면분식",
    54: "국물",
    55: "국물",
    56: "반찬단품",
    63: "반찬단품",
}

# 양념류 (key_ingredients에서 제외)
SEASONING_SET = frozenset({
    "소금", "설탕", "간장", "된장", "고추장", "고춧가루", "참기름", "들기름",
    "식용유", "올리브유", "버터", "마요네즈", "케첩", "식초", "후추", "깨",
    "통깨", "다진마늘", "마늘", "생강", "국간장", "진간장", "맛술", "미림",
    "올리고당", "물엿", "굴소스", "쌈장", "멸치액젓", "까나리액젓",
    "춘장", "카레가루", "후춧가루", "파슬리", "바질", "로즈마리",
    "소금", "물", "얼음", "기름",
})


def get_session() -> Session:
    """DB 세션 생성 + 테이블 자동 생성"""
    create_tables()
    return SessionLocal()


def is_duplicate(db: Session, source_url: str) -> bool:
    """source_url 기준 중복 체크"""
    return (
        db.query(ReferenceRecipe)
        .filter(ReferenceRecipe.source_url == source_url)
        .first()
        is not None
    )


def save_recipe(db: Session, data: dict) -> bool:
    """레퍼런스 레시피 저장 (중복 스킵). 저장 성공 시 True."""
    if is_duplicate(db, data["source_url"]):
        return False

    recipe = ReferenceRecipe(**data)
    db.add(recipe)
    try:
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def polite_delay(min_s: float = 1.0, max_s: float = 2.5) -> None:
    """Rate limiting: 랜덤 딜레이"""
    time.sleep(random.uniform(min_s, max_s))


def extract_key_ingredients(all_ingredients: list[str], max_count: int = 5) -> list[str]:
    """전체 재료에서 양념류 제외하고 핵심 재료 추출"""
    key: list[str] = []
    for ing in all_ingredients:
        # 분량 제거: "김치 200g" → "김치"
        cleaned = re.sub(
            r"\d+[./]?\d*\s*"
            r"(g|kg|ml|L|큰술|작은술|컵|개|장|쪽|알|줌|꼬집|조각|봉지|팩|통|캔|약간|조금|적당량)?",
            "", ing,
        ).strip()
        cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()

        if not cleaned:
            continue

        # 양념류 필터 (정확 매칭 + 부분 매칭)
        if cleaned in SEASONING_SET:
            continue
        if any(len(s) >= 2 and s in cleaned for s in SEASONING_SET):
            continue

        if cleaned not in key:
            key.append(cleaned)

        if len(key) >= max_count:
            break

    return key


def generate_technique_heuristic(steps: list[str]) -> str | None:
    """조리 스텝에서 핵심 기법 추출 (시간·불세기·비율 포함 문장 우선)"""
    important_re = re.compile(
        r"(분|초|센불|중불|약불|중약불|중강불|도|℃|비율|:|\d+큰술|\d+작은술)"
    )

    candidates = []
    for step in steps:
        if important_re.search(step):
            text = step[:100] if len(step) > 100 else step
            candidates.append(text)

    if candidates:
        return " ".join(candidates[:2])
    return None
