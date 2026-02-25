"""폴백 레시피 템플릿 풀 - LLM 실패 시 카테고리별 다양한 레시피 제공"""
from __future__ import annotations

import random

FALLBACK_TEMPLATES = [
    # ── 밥 (4개) ──────────────────────────────────────────
    {
        "category": "밥",
        "title_fmt": "{} 볶음밥",
        "summary": "냉장고 재료로 뚝딱 만드는 간단 볶음밥",
        "base_ings": ["밥", "간장", "참기름"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 먹기 좋게 썰어 준비합니다.",
            f"팬에 기름을 두르고 중불에서 {main}을(를) 1분간 볶습니다.",
            "밥을 넣고 중강불에서 2분간 고루 볶아줍니다.",
            "간장 1큰술을 팬 가장자리에 둘러 넣고 30초간 볶아 풍미를 냅니다.",
            "불을 끄고 참기름을 둘러 마무리합니다.",
        ],
        "tips": ["센불에서 빠르게 볶아야 밥알이 살아있어요."],
    },
    {
        "category": "밥",
        "title_fmt": "{} 덮밥",
        "summary": "재료를 볶아 밥 위에 올리는 간편 한 그릇",
        "base_ings": ["밥", "간장", "설탕"],
        "steps_fn": lambda main, rest: [
            f"{main}을(를) 한입 크기로 썰어줍니다.",
            f"팬에 기름을 두르고 중불에서 {main}을(를) 2분간 노릇하게 볶습니다.",
            *(
                [f"{', '.join(rest)}을(를) 넣고 중불에서 1분 더 볶습니다."]
                if rest
                else []
            ),
            "간장 1큰술과 설탕 약간을 넣고 센불에서 30초간 빠르게 볶습니다.",
            "그릇에 밥을 담고 볶은 재료를 올려 완성합니다.",
        ],
        "tips": ["간장을 넣은 뒤 센불에서 빠르게 볶아야 캐러멜 향이 나요."],
    },
    {
        "category": "밥",
        "title_fmt": "{} 비빔밥",
        "summary": "고추장과 참기름으로 비벼 먹는 영양 비빔밥",
        "base_ings": ["밥", "고추장", "참기름"],
        "steps_fn": lambda main, rest: [
            f"{main}을(를) 채 썰어 준비합니다.",
            f"팬에 기름을 두르고 중불에서 {main}을(를) 1분간 볶습니다.",
            *(
                [f"{', '.join(rest)}을(를) 넣고 중불에서 30초간 함께 볶습니다."]
                if rest
                else []
            ),
            "그릇에 밥을 담고 볶은 재료를 올려줍니다.",
            "고추장 1큰술과 참기름을 넣고 잘 비벼서 완성합니다.",
        ],
        "tips": ["참기름을 넉넉히 넣으면 더 고소해요."],
    },
    {
        "category": "밥",
        "title_fmt": "{} 주먹밥",
        "summary": "한입에 쏙 들어가는 간편 주먹밥",
        "base_ings": ["밥", "소금", "참기름"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 잘게 다져줍니다.",
            "볼에 밥과 다진 재료를 넣습니다.",
            "소금 약간과 참기름 1작은술을 넣고 골고루 섞어줍니다.",
            "한입 크기로 동그랗게 빚어줍니다.",
            "김이 있으면 감싸서 완성합니다.",
        ],
        "tips": ["손에 참기름을 살짝 바르면 밥이 안 달라붙어요."],
    },
    # ── 국물 (3개) ─────────────────────────────────────────
    {
        "category": "국물",
        "title_fmt": "{} 찌개",
        "summary": "된장과 고추장으로 깊은 맛을 내는 찌개",
        "base_ings": ["된장", "고추장", "물"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 먹기 좋게 썰어줍니다.",
            "냄비에 물 2컵(400ml)을 넣고 강불에서 끓입니다.",
            "된장 1큰술을 풀어 넣고 중불로 줄입니다.",
            f"{main}을(를) 넣고 중불에서 3분간 끓입니다.",
            "고추장 1작은술을 넣고 2분 더 끓여 완성합니다.",
        ],
        "tips": ["된장을 먼저 풀어야 국물 맛이 균일해요."],
    },
    {
        "category": "국물",
        "title_fmt": "{} 계란국",
        "summary": "부드러운 계란과 함께 끓이는 맑은 국",
        "base_ings": ["계란", "소금", "물"],
        "steps_fn": lambda main, rest: [
            f"{main}을(를) 얇게 썰어줍니다.",
            "냄비에 물 2컵(400ml)을 넣고 강불에서 끓입니다.",
            f"{main}을(를) 넣고 중불에서 2분간 끓입니다.",
            *(
                [f"{', '.join(rest)}을(를) 넣고 중불에서 1분 더 끓입니다."]
                if rest
                else []
            ),
            "계란을 풀어 천천히 넣고 소금으로 간을 맞춥니다.",
            "약불에서 30초 후 불을 끄고 완성합니다.",
        ],
        "tips": ["계란을 넣은 후 젓지 않아야 꽃 모양이 예뻐요."],
    },
    {
        "category": "국물",
        "title_fmt": "{} 수프",
        "summary": "부드럽고 크리미한 간편 수프",
        "base_ings": ["우유", "소금", "버터"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 잘게 다져줍니다.",
            "냄비에 버터 1큰술을 녹이고 약불에서 1분간 볶습니다.",
            f"{main}을(를) 넣고 중불에서 2분간 볶아줍니다.",
            "우유 1컵(200ml)을 넣고 약불에서 3분간 저으며 끓입니다.",
            "소금으로 간을 맞추고 완성합니다.",
        ],
        "tips": ["우유를 넣은 후 약불로 줄여야 분리되지 않아요."],
    },
    # ── 반찬단품 (5개) ──────────────────────────────────────
    {
        "category": "반찬단품",
        "title_fmt": "{} 볶음",
        "summary": "간장 양념으로 볶아낸 간단 반찬",
        "base_ings": ["간장", "참기름", "설탕"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 먹기 좋게 썰어줍니다.",
            f"팬에 기름을 두르고 중불에서 {main}을(를) 2분간 볶습니다.",
            *(
                [f"{', '.join(rest)}을(를) 넣고 중불에서 1분 더 볶습니다."]
                if rest
                else []
            ),
            "간장 1큰술과 설탕 약간을 넣고 센불에서 30초간 볶습니다.",
            "불을 끄고 참기름을 둘러 마무리합니다.",
        ],
        "tips": ["센불에서 빠르게 볶아야 식감이 살아요."],
    },
    {
        "category": "반찬단품",
        "title_fmt": "{} 계란말이",
        "summary": "재료를 넣어 돌돌 말아낸 계란말이",
        "base_ings": ["계란", "소금", "기름"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 잘게 다져줍니다.",
            "계란 2개를 풀고 다진 재료와 소금 약간을 넣어 섞어줍니다.",
            "팬에 기름을 두르고 약불로 달궈줍니다.",
            "계란물을 1/3씩 3번에 나누어 붓고 돌돌 말아줍니다.",
            "1분간 식힌 후 먹기 좋게 썰어 완성합니다.",
        ],
        "tips": ["약불에서 천천히 말아야 찢어지지 않아요."],
    },
    {
        "category": "반찬단품",
        "title_fmt": "{}전",
        "summary": "밀가루 반죽에 부쳐낸 바삭한 전",
        "base_ings": ["밀가루", "계란", "기름"],
        "steps_fn": lambda main, rest: [
            f"{main}을(를) 얇게 썰어줍니다.",
            "밀가루 3큰술과 물 4큰술을 섞어 반죽을 만듭니다.",
            f"{main}에 밀가루를 살짝 묻힌 후 계란물을 입혀줍니다.",
            "팬에 기름을 넉넉히 두르고 중불에서 앞뒤로 2분씩 노릇하게 부칩니다.",
            "키친타월에 올려 기름을 빼고 완성합니다.",
        ],
        "tips": ["반죽을 너무 두껍게 입히면 눅눅해져요."],
    },
    {
        "category": "반찬단품",
        "title_fmt": "{} 무침",
        "summary": "새콤달콤 고추장 양념 무침",
        "base_ings": ["고추장", "식초", "설탕"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 한입 크기로 준비합니다.",
            "고추장 1큰술, 식초 1큰술, 설탕 약간으로 양념장을 만듭니다.",
            "볼에 재료를 담고 양념장을 넣어 골고루 버무립니다.",
            "깨를 뿌려 완성합니다.",
        ],
        "tips": ["버무린 후 바로 먹어야 식감이 좋아요."],
    },
    {
        "category": "반찬단품",
        "title_fmt": "{} 조림",
        "summary": "간장 양념에 졸여낸 밥도둑 조림",
        "base_ings": ["간장", "설탕", "물"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 한입 크기로 썰어줍니다.",
            "간장 2큰술, 설탕 1큰술, 물 반 컵(100ml)으로 양념을 만듭니다.",
            f"냄비에 {main}과 양념을 넣고 중불에서 끓입니다.",
            "끓어오르면 약불로 줄이고 5분간 졸여 완성합니다.",
        ],
        "tips": ["약불에서 천천히 졸여야 양념이 골고루 배요."],
    },
    # ── 면분식 (3개) ─────────────────────────────────────
    {
        "category": "면분식",
        "title_fmt": "{} 볶음면",
        "summary": "재료를 넣고 볶아낸 간편 볶음면",
        "base_ings": ["라면사리", "간장", "기름"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 채 썰어줍니다.",
            "라면사리를 끓는 물에 2분간 삶아 건져줍니다.",
            f"팬에 기름을 두르고 중불에서 {main}을(를) 1분간 볶습니다.",
            "삶은 면을 넣고 간장 1큰술을 넣어 센불에서 1분간 볶아 완성합니다.",
        ],
        "tips": ["면을 살짝 덜 삶아야 볶을 때 불지 않아요."],
    },
    {
        "category": "면분식",
        "title_fmt": "{} 라면",
        "summary": "재료를 추가한 든든한 라면",
        "base_ings": ["라면", "물"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 먹기 좋게 썰어줍니다.",
            "냄비에 물 550ml를 넣고 강불에서 끓입니다.",
            "스프와 면을 넣고 중불에서 3분간 끓입니다.",
            f"{main}을(를) 넣고 1분 더 끓여 완성합니다.",
        ],
        "tips": ["재료를 면과 동시에 넣으면 익는 시간을 맞추기 어려워요."],
    },
    {
        "category": "면분식",
        "title_fmt": "{} 떡볶이",
        "summary": "매콤달콤 고추장 양념 떡볶이",
        "base_ings": ["떡", "고추장", "설탕"],
        "steps_fn": lambda main, rest: [
            f"{main}{'과 ' + ', '.join(rest) if rest else ''}을(를) 먹기 좋게 썰어줍니다.",
            "냄비에 물 1컵(200ml), 고추장 1.5큰술, 설탕 1큰술을 넣고 중불에서 끓입니다.",
            "떡을 넣고 중불에서 3분간 끓입니다.",
            f"{main}을(를) 넣고 2분 더 끓입니다.",
            "약불로 줄이고 1분간 졸여 완성합니다.",
        ],
        "tips": ["떡이 부드러워질 때까지 충분히 끓여주세요."],
    },
]

# 카테고리별 인덱스 맵 (모듈 로드 시 자동 구축)
_CATEGORY_MAP: dict[str, list[int]] = {}
for _i, _t in enumerate(FALLBACK_TEMPLATES):
    _CATEGORY_MAP.setdefault(_t["category"], []).append(_i)

CATEGORIES = list(_CATEGORY_MAP.keys())


def pick_diverse_templates(count: int = 3) -> list[dict]:
    """서로 다른 카테고리에서 count개 템플릿 선택"""
    cats = list(CATEGORIES)
    random.shuffle(cats)
    picked: list[dict] = []
    used_indices: set[int] = set()
    for cat in cats:
        if len(picked) >= count:
            break
        idx = random.choice(_CATEGORY_MAP[cat])
        picked.append(FALLBACK_TEMPLATES[idx])
        used_indices.add(idx)
    # 카테고리 부족 시 나머지 랜덤
    while len(picked) < count:
        idx = random.randint(0, len(FALLBACK_TEMPLATES) - 1)
        if idx not in used_indices:
            picked.append(FALLBACK_TEMPLATES[idx])
            used_indices.add(idx)
    return picked
