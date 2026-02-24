from __future__ import annotations

import logging

from app.data.allergen_derivatives import expand_exclusions
from app.models.recommendation import RecommendationCreate, RecommendationResponse

logger = logging.getLogger(__name__)

# 조리 단계에서 명시적으로 언급 안 해도 되는 기본 재료
_IMPLICIT_INGREDIENTS = {
    "소금", "후추", "물", "기름", "식용유", "올리브유", "참기름", "들기름",
    "설탕", "소스", "식초", "깨", "통깨", "깨소금", "후춧가루",
}


def _check_ingredient_step_consistency(
    title: str, ingredients: list[str], steps: list[str],
) -> list[str]:
    """
    제목에 포함된 재료가 조리 단계에서 실제로 사용되는지 검증

    Returns:
        조리 단계에서 빠진 제목 재료 목록
    """
    steps_text = " ".join(steps)
    missing = []

    for ing in ingredients:
        ing_clean = ing.strip()
        if not ing_clean or ing_clean in _IMPLICIT_INGREDIENTS:
            continue
        # 제목에 포함된 재료만 필수 체크 (핵심 재료)
        if ing_clean in title and ing_clean not in steps_text:
            missing.append(ing_clean)

    return missing


def validate_response(resp: RecommendationResponse, req: RecommendationCreate) -> None:
    # hard rules
    if len(resp.recipes) != 3:
        raise ValueError("recipes_must_be_3")

    for r in resp.recipes:
        if r.time_min > req.constraints.time_limit_min:
            raise ValueError("time_limit_exceeded")

        # exclude(알레르기/제외 재료) 포함 금지 - 파생 재료까지 확장
        excl = expand_exclusions(req.constraints.exclude)

        # 텍스트 전체를 소문자로 변환하여 검사
        text_blob = " ".join(
            [
                r.title,
                r.summary,
                " ".join(r.ingredients_have),
                " ".join(r.ingredients_need),
                " ".join(r.steps),
            ]
        ).lower()

        for e in excl:
            if e and e in text_blob:
                raise ValueError(f"exclude_ingredient_detected: {e}")

        quality = req.constraints.quality_level
        if quality == "fast":
            valid_steps = 2 <= len(r.steps) <= 8
        elif quality == "detailed":
            valid_steps = 4 <= len(r.steps) <= 12
        else:
            valid_steps = 4 <= len(r.steps) <= 8

        if not valid_steps:
            raise ValueError("steps_length_invalid")

        # 제목 재료가 조리 단계에서 사용되는지 검증 (경고, 캐시 방지용)
        missing = _check_ingredient_step_consistency(
            r.title, r.ingredients_total, r.steps
        )
        if missing:
            logger.warning(
                f"[품질] '{r.title}' 제목 재료 {missing}가 조리 단계에 없음"
            )
            resp._skip_cache = True  # type: ignore[attr-defined]
