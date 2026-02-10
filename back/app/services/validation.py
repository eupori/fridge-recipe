from __future__ import annotations

from app.data.allergen_derivatives import expand_exclusions
from app.models.recommendation import RecommendationCreate, RecommendationResponse


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

        if not (4 <= len(r.steps) <= 8):
            raise ValueError("steps_length_invalid")
