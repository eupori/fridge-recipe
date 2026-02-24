"""
재료 입력 검증 — 비식품/위험 재료 차단

사용자가 입력한 재료 목록에서 식품이 아닌 항목을 감지합니다.
"""

from __future__ import annotations

import re

# 절대 식품이 아닌 항목 (독성, 화학물, 금속 등)
NON_FOOD_BLOCKLIST: set[str] = {
    # 독성 식물/버섯
    "독버섯", "독초", "독미나리", "투구꽃", "협죽도", "미치광이풀",
    "광대버섯", "독우산광대버섯", "화경솔밭버섯", "개나리버섯",
    # 금속/광물
    "금속", "철", "구리", "납", "수은", "알루미늄", "아연",
    "니켈", "카드뮴", "비소", "크롬", "주석",
    # 화학물질/세제
    "세제", "표백제", "락스", "염산", "황산", "암모니아",
    "시너", "페인트", "접착제", "본드", "농약", "살충제",
    "비료", "제초제", "방부제", "포름알데히드", "메탄올",
    "에탄올", "아세톤", "벤젠", "톨루엔",
    # 의약품/약물
    "수면제", "진통제", "마약", "대마", "아편",
    # 비식품 일상용품
    "플라스틱", "비닐", "스티로폼", "종이", "휴지",
    "건전지", "배터리", "고무", "시멘트", "석면",
    "유리", "모래", "흙", "돌",
}

# 패턴 기반 차단 (정규식)
NON_FOOD_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"독(?:이\s*있|성)"),      # "독이 있는", "독성"
    re.compile(r"살충|살균제|소독"),        # 살충제, 살균제, 소독
    re.compile(r"화학|약품"),              # 화학물질, 약품
]


MAX_INGREDIENT_LENGTH = 30
# 허용 문자: 한글, 영문, 숫자, 공백, 하이픈, 괄호
_ALLOWED_CHARS = re.compile(r"[^가-힣a-zA-Z0-9\s\-()]")


def sanitize_ingredient(name: str) -> str:
    """재료명 정제 (프롬프트 인젝션 방지)"""
    name = name.strip()
    # 허용되지 않는 문자 제거
    name = _ALLOWED_CHARS.sub("", name)
    # 길이 제한
    name = name[:MAX_INGREDIENT_LENGTH]
    # 공백 정리
    name = " ".join(name.split())
    return name


def sanitize_ingredients(ingredients: list[str]) -> list[str]:
    """재료 목록 정제"""
    return [s for s in (sanitize_ingredient(i) for i in ingredients) if s]


def validate_ingredients(ingredients: list[str]) -> list[str]:
    """
    비식품 재료를 감지하여 목록으로 반환합니다.

    Returns:
        차단된 재료명 리스트 (비어 있으면 모두 통과)
    """
    blocked: list[str] = []

    for ingredient in ingredients:
        name = ingredient.strip().lower()
        if not name:
            continue

        # 1. 블록리스트 직접 매칭
        if name in NON_FOOD_BLOCKLIST:
            blocked.append(ingredient)
            continue

        # 2. 블록리스트 부분 매칭 (재료명에 포함된 경우)
        if any(term in name for term in NON_FOOD_BLOCKLIST):
            blocked.append(ingredient)
            continue

        # 3. 패턴 매칭
        if any(pat.search(name) for pat in NON_FOOD_PATTERNS):
            blocked.append(ingredient)
            continue

    return blocked
