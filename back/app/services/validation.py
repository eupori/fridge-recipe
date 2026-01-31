from __future__ import annotations

from app.models.recommendation import RecommendationCreate, RecommendationResponse


def validate_response(resp: RecommendationResponse, req: RecommendationCreate) -> None:
    # hard rules
    if len(resp.recipes) != 3:
        raise ValueError("recipes_must_be_3")

    for r in resp.recipes:
        if r.time_min > req.constraints.time_limit_min:
            raise ValueError("time_limit_exceeded")

        # exclude(알레르기/제외 재료) 포함 금지
        excl = {e.strip() for e in req.constraints.exclude if e.strip()}
        text_blob = " ".join([r.title, r.summary, " ".join(r.ingredients_have), " ".join(r.ingredients_need), " ".join(r.steps)])
        for e in excl:
            if e and e in text_blob:
                raise ValueError("exclude_ingredient_detected")

        if not (4 <= len(r.steps) <= 8):
            raise ValueError("steps_length_invalid")
