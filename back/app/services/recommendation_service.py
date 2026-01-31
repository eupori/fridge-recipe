from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    Recipe,
    ShoppingItem,
)
from app.services.validation import validate_response

# NOTE: MVP용 인메모리 저장소(배포/재시작 시 사라짐)
_STORE: dict[str, RecommendationResponse] = {}


def create_recommendation(payload: RecommendationCreate) -> RecommendationResponse:
    # TODO: LLM 연동 전까지는 더미 응답
    rec = RecommendationResponse(
        id=f"rec_{uuid4().hex[:10]}",
        created_at=datetime.now(timezone.utc),
        recipes=[
            Recipe(
                title="김치계란볶음밥(초간단)",
                time_min=12,
                servings=payload.constraints.servings,
                summary="남은 김치/밥으로 1팬에 끝내는 자취 필살기",
                ingredients_have=[i for i in payload.ingredients if i],
                ingredients_need=["밥"] if "밥" not in payload.ingredients else [],
                steps=[
                    "프라이팬에 기름을 두르고 김치를 2분 볶아요.",
                    "밥을 넣고 3분 볶아 고슬고슬하게 만들어요.",
                    "한쪽에 공간을 내고 계란을 풀어 스크램블해요.",
                    "모두 섞고 간장/소금으로 간을 맞춰요."
                ],
                tips=["밥이 없으면 식빵/또띠아로도 변형 가능해요."],
            ),
            Recipe(
                title="두부간장조림(전자레인지 버전)",
                time_min=10,
                servings=payload.constraints.servings,
                summary="썰어서 양념 뿌리고 돌리면 끝",
                ingredients_have=[i for i in payload.ingredients if i],
                ingredients_need=["간장"] if "간장" not in payload.ingredients else [],
                steps=[
                    "두부를 1~2cm로 썰어요.",
                    "간장+물+설탕(또는 올리고당)을 섞어 양념을 만들어요.",
                    "두부 위에 양념과 파(있으면)를 올려요.",
                    "전자레인지에 2~3분 돌려 마무리해요."
                ],
                tips=["매콤하게 먹고 싶으면 고춧가루를 조금 넣어요."],
            ),
            Recipe(
                title="양파달걀국(초간단)",
                time_min=8,
                servings=payload.constraints.servings,
                summary="속 편한 국물 한 그릇",
                ingredients_have=[i for i in payload.ingredients if i],
                ingredients_need=["소금"] if "소금" not in payload.ingredients else [],
                steps=[
                    "물에 양파를 넣고 3분 끓여요.",
                    "간을 소금(또는 국간장)으로 맞춰요.",
                    "계란을 풀어 넣고 젓지 말고 30초 두어요.",
                    "한 번만 가볍게 저어 마무리해요."
                ],
                tips=["다진마늘이 있으면 0.5티스푼만 넣어도 맛이 올라가요."],
            ),
        ],
        shopping_list=[
            ShoppingItem(item="밥", qty=None, unit=None, category="주식"),
            ShoppingItem(item="간장", qty=1, unit="병", category="양념"),
        ],
    )

    validate_response(rec, payload)
    _STORE[rec.id] = rec
    return rec


def get_recommendation(recommendation_id: str) -> RecommendationResponse | None:
    return _STORE.get(recommendation_id)
