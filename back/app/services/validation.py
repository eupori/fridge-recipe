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


def _auto_fix_missing_ingredients(recipe, missing_ingredients: list[str]) -> None:
    """
    조리 단계에서 빠진 핵심 재료를 자동으로 삽입

    전략: "재료" 라는 단어가 있는 단계에 구체적 재료명을 삽입하거나,
    적절한 위치에 새 단계를 추가
    """
    steps = recipe.steps
    if not steps or not missing_ingredients:
        return

    for ing in missing_ingredients:
        # 1차: "재료를 넣" 같은 제네릭 표현이 있는 단계에 구체적 재료명 삽입
        fixed = False
        for i, step in enumerate(steps):
            if "재료를" in step or "재료" in step:
                steps[i] = step.replace("재료를", f"{ing}을(를)", 1)
                fixed = True
                break

        if not fixed:
            # 2차: 마지막에서 하나 전에 "{재료}을(를) 넣고 섞는다" 단계 추가
            insert_idx = max(1, len(steps) - 1)
            steps.insert(insert_idx, f"{ing}을(를) 넣고 잘 섞는다")


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

        # 제목 재료가 조리 단계에서 사용되는지 검증 + 자동 보정
        missing = _check_ingredient_step_consistency(
            r.title, r.ingredients_total, r.steps
        )
        if missing:
            logger.warning(
                f"[품질] '{r.title}' 제목 재료 {missing}가 조리 단계에 없음 → 자동 보정"
            )
            _auto_fix_missing_ingredients(r, missing)
            resp._skip_cache = True  # type: ignore[attr-defined]
