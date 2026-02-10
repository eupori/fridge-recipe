"""알러지 재료와 파생 재료 매핑"""

ALLERGEN_DERIVATIVES: dict[str, list[str]] = {
    # 토마토
    "토마토": [
        "케첩",
        "토마토소스",
        "토마토페이스트",
        "토마토퓨레",
        "파스타소스",
        "피자소스",
        "마리나라소스",
    ],
    # 유제품
    "우유": [
        "치즈",
        "버터",
        "크림",
        "생크림",
        "요거트",
        "요구르트",
        "분유",
        "연유",
        "휘핑크림",
        "모짜렐라",
    ],
    # 계란
    "계란": ["달걀", "난황", "난백", "마요네즈", "마요"],
    # 땅콩/견과류
    "땅콩": ["피넛버터", "땅콩버터", "땅콩소스"],
    # 대두
    "대두": ["두부", "된장", "간장", "청국장", "콩나물", "두유", "미소", "콩"],
    # 밀/글루텐
    "밀": ["밀가루", "빵가루", "파스타", "국수", "라면", "우동", "소면", "스파게티", "빵"],
    # 갑각류
    "갑각류": ["새우", "게", "랍스터", "가재", "새우젓", "게장"],
    "새우": ["새우젓"],
    # 생선
    "생선": ["멸치", "참치", "연어", "고등어", "어묵", "액젓", "피시소스", "멸치액젓"],
}


def get_all_derivatives(allergen: str) -> set[str]:
    """알러지 재료와 모든 파생 재료 반환"""
    allergen_normalized = allergen.strip().lower()
    result = {allergen_normalized}

    for base, derivatives in ALLERGEN_DERIVATIVES.items():
        base_lower = base.lower()
        derivatives_lower = [d.lower() for d in derivatives]

        # allergen이 base거나 derivatives에 포함되면 전체 그룹 추가
        if allergen_normalized == base_lower or allergen_normalized in derivatives_lower:
            result.add(base_lower)
            result.update(derivatives_lower)

    return result


def expand_exclusions(exclusions: list[str]) -> set[str]:
    """제외 재료 목록을 파생 재료까지 확장"""
    expanded = set()
    for excl in exclusions:
        if excl and excl.strip():
            expanded.update(get_all_derivatives(excl.strip()))
    return expanded
