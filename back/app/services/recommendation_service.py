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
    # 입력 재료 정규화(공백 제거 + 중복 제거)
    ing_set = {i.strip() for i in payload.ingredients if i and i.strip()}

    # MVP 더미 레시피라도 "총재료/보유/추가"가 일관되게 나오도록 레시피별 필수 재료를 선언
    # NOTE: 기본 양념(소금/후추/식용유 등)은 '자동 가정'하지 않음(요구사항: 빼는 걸로).
    def img(q: str) -> str:
        # 키 없이도 동작하는 간단한 이미지 소스(Unsplash). v2에서 정식 API/저작권 표기 고도화.
        # NOTE: 한국어 쿼리는 결과가 약할 수 있어 영어 키워드도 함께 사용 권장.
        from urllib.parse import quote

        return f"https://source.unsplash.com/featured/?{quote(q)}"

    def split_have_need(required: set[str]) -> tuple[list[str], list[str]]:
        have = sorted(list(required & ing_set))
        need = sorted(list(required - ing_set))
        return have, need

    def total(required: set[str]) -> list[str]:
        return sorted(list(required))

    recipes: list[Recipe] = []

    # 1) 김치계란볶음밥
    req1 = {"김치", "계란", "밥"}
    have1, need1 = split_have_need(req1)
    recipes.append(
        Recipe(
            title="김치계란볶음밥(초간단)",
            time_min=12,
            servings=payload.constraints.servings,
            summary="남은 김치/밥으로 1팬에 끝내는 자취 필살기",
            image_url=img("kimchi fried rice"),
            ingredients_total=total(req1),
            ingredients_have=have1,
            ingredients_need=need1,
            steps=[
                "프라이팬에 기름을 두르고 김치를 2분 볶아요.",
                "밥을 넣고 3분 볶아 고슬고슬하게 만들어요.",
                "한쪽에 공간을 내고 계란을 풀어 스크램블해요.",
                "모두 섞고 간장/소금으로 간을 맞춰요(있으면)."
            ],
            tips=["밥이 없으면 식빵/또띠아로도 변형 가능해요."],
        )
    )

    # 2) 두부간장조림
    req2 = {"두부", "간장"}
    have2, need2 = split_have_need(req2)
    recipes.append(
        Recipe(
            title="두부간장조림(전자레인지 버전)",
            time_min=10,
            servings=payload.constraints.servings,
            summary="썰어서 양념 뿌리고 돌리면 끝",
            image_url=img("tofu"),
            ingredients_total=total(req2),
            ingredients_have=have2,
            ingredients_need=need2,
            steps=[
                "두부를 1~2cm로 썰어요.",
                "간장+물+설탕(또는 올리고당)을 섞어 양념을 만들어요(있으면).",
                "두부 위에 양념과 파(있으면)를 올려요.",
                "전자레인지에 2~3분 돌려 마무리해요."
            ],
            tips=["매콤하게 먹고 싶으면 고춧가루를 조금 넣어요(있으면)."],
        )
    )

    # 3) 양파달걀국
    req3 = {"양파", "계란", "소금"}
    have3, need3 = split_have_need(req3)
    recipes.append(
        Recipe(
            title="양파달걀국(초간단)",
            time_min=8,
            servings=payload.constraints.servings,
            summary="속 편한 국물 한 그릇",
            image_url=img("egg soup"),
            ingredients_total=total(req3),
            ingredients_have=have3,
            ingredients_need=need3,
            steps=[
                "물에 양파를 넣고 3분 끓여요.",
                "간을 소금(또는 국간장)으로 맞춰요.",
                "계란을 풀어 넣고 젓지 말고 30초 두어요.",
                "한 번만 가볍게 저어 마무리해요."
            ],
            tips=["다진마늘을 넣어도 좋아요(있으면)."],
        )
    )

    # 장보기 리스트는 recipes[].ingredients_need를 합쳐서 생성
    need_items: set[str] = set()
    for r in recipes:
        need_items |= {x for x in r.ingredients_need if x}

    rec = RecommendationResponse(
        id=f"rec_{uuid4().hex[:10]}",
        created_at=datetime.now(timezone.utc),
        recipes=recipes,
        shopping_list=[ShoppingItem(item=i) for i in sorted(list(need_items))],
    )

    validate_response(rec, payload)
    _STORE[rec.id] = rec
    return rec


def get_recommendation(recommendation_id: str) -> RecommendationResponse | None:
    return _STORE.get(recommendation_id)
