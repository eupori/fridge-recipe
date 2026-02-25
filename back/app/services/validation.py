from __future__ import annotations

import logging
import re

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


def _check_ingredient_usage_rate(recipe) -> float:
    """ingredients_total 중 steps에 언급된 비율 반환 (0.0~1.0)"""
    steps_text = " ".join(recipe.steps)
    total = [i for i in recipe.ingredients_total if i.strip() and i.strip() not in _IMPLICIT_INGREDIENTS]
    if not total:
        return 1.0
    mentioned = sum(1 for ing in total if ing in steps_text)
    return mentioned / len(total)


_TIME_PATTERN = re.compile(r'\d+\s*분|\d+\s*초')
_HEAT_KEYWORDS = {"강불", "중불", "약불", "센불", "중강불", "중약불"}
_STATE_KEYWORDS = {"노릇", "투명", "걸쭉", "끓기", "녹으면", "익으면", "줄어들면", "끓으면", "부글"}


def _check_step_specificity(steps: list[str]) -> dict:
    """조리 단계의 구체성 분석. {time_ratio, heat_ratio, state_ratio} 반환"""
    if not steps:
        return {"time_ratio": 0.0, "heat_ratio": 0.0, "state_ratio": 0.0}

    time_count = sum(1 for s in steps if _TIME_PATTERN.search(s))
    heat_count = sum(1 for s in steps if any(k in s for k in _HEAT_KEYWORDS))
    state_count = sum(1 for s in steps if any(k in s for k in _STATE_KEYWORDS))
    n = len(steps)

    return {
        "time_ratio": time_count / n,
        "heat_ratio": heat_count / n,
        "state_ratio": state_count / n,
    }


_STYLE_KEYWORDS = {
    "볶": "볶음", "구이": "구이", "굽": "구이",
    "끓": "국물", "찌개": "국물", "국": "국물", "탕": "국물",
    "전": "전", "부침": "전",
    "무침": "무침", "비빔": "무침", "버무": "무침",
    "조림": "조림", "졸": "조림",
    "찜": "찜", "삶": "찜",
    "면": "면", "파스타": "면", "라면": "면",
    "밥": "밥", "볶음밥": "밥", "덮밥": "밥", "비빔밥": "밥",
}


def _check_style_diversity(recipes) -> bool:
    """3개 레시피의 스타일이 모두 같으면 False 반환"""
    styles = []
    for r in recipes:
        text = r.title + " " + " ".join(r.steps)
        detected = set()
        for keyword, style in _STYLE_KEYWORDS.items():
            if keyword in text:
                detected.add(style)
        styles.append(detected)

    # 모든 레시피가 공통으로 가진 스타일만 있으면 다양성 부족
    if len(styles) >= 2:
        common = styles[0]
        for s in styles[1:]:
            common = common & s
        # 모든 레시피의 스타일 합집합이 공통 부분과 같으면 → 모두 같은 스타일
        all_styles = set()
        for s in styles:
            all_styles |= s
        if all_styles and all_styles == common:
            return False
    return True


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

    # --- soft validations (경고 + 캐시 스킵, hard error 아님) ---
    try:
        quality = req.constraints.quality_level

        # S1. 재료 사용률
        for r in resp.recipes:
            usage = _check_ingredient_usage_rate(r)
            if usage < 0.6:
                logger.warning(
                    f"[품질] '{r.title}' 재료 사용률 {usage:.0%} (60% 미만) → 캐시 스킵"
                )
                resp._skip_cache = True  # type: ignore[attr-defined]

        # S2. 조리 단계 구체성
        for r in resp.recipes:
            spec = _check_step_specificity(r.steps)
            if quality in ("standard", "detailed") and spec["time_ratio"] < 0.5:
                logger.warning(
                    f"[품질] '{r.title}' 시간 표현 {spec['time_ratio']:.0%} (50% 미만) → 캐시 스킵"
                )
                resp._skip_cache = True  # type: ignore[attr-defined]
            if quality == "detailed" and spec["heat_ratio"] < 0.5:
                logger.warning(
                    f"[품질] '{r.title}' 불세기 표현 {spec['heat_ratio']:.0%} (50% 미만) → 캐시 스킵"
                )
                resp._skip_cache = True  # type: ignore[attr-defined]

        # S3. 스타일 다양성
        if not _check_style_diversity(resp.recipes):
            titles = [r.title for r in resp.recipes]
            logger.warning(
                f"[품질] 스타일 다양성 부족: {titles} → 캐시 스킵"
            )
            resp._skip_cache = True  # type: ignore[attr-defined]
    except Exception as e:
        logger.warning(f"[품질] soft 검증 중 오류 (무시): {e}")
