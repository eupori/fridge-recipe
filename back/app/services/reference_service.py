"""
레퍼런스 수집 서비스 - DB 역색인 기반 레시피 레퍼런스 수집

큐레이션 DB에서 역색인 매칭으로 관련 레퍼런스를 수집하고
LLM 프롬프트에 삽입할 포맷 텍스트를 반환합니다.
"""

from __future__ import annotations

import logging
import math
import random
import re

from app.data.ingredient_synonyms import INGREDIENT_SYNONYMS

logger = logging.getLogger(__name__)


# ── 역색인 헬퍼 ──────────────────────────────────────────

# 역방향 동의어 맵: 정규형 → 동의어 집합
_REVERSE_SYNONYMS: dict[str, set[str]] = {}
for _syn, _canon in INGREDIENT_SYNONYMS.items():
    _REVERSE_SYNONYMS.setdefault(_canon, set()).add(_syn)


def _normalize_for_index(name: str) -> str:
    """재료명 정규화 (소문자 + 공백 제거)"""
    return re.sub(r"\s+", "", name.strip().lower())


def _all_forms(name: str) -> set[str]:
    """동의어 확장: 정규화된 모든 형태 반환 (정규형 + 동의어 그룹 전체)"""
    lower = name.strip().lower()
    normalized = _normalize_for_index(lower)
    forms = {normalized}
    # 원본 → 정규형 찾기
    canon = INGREDIENT_SYNONYMS.get(lower) or INGREDIENT_SYNONYMS.get(normalized)
    if canon:
        canon_norm = _normalize_for_index(canon)
        forms.add(canon_norm)
        # 정규형의 모든 동의어 추가 (삼겹살→돼지고기→{목살,삼겹살})
        for syn in _REVERSE_SYNONYMS.get(canon, set()):
            forms.add(_normalize_for_index(syn))
    # 자기 자신이 정규형인 경우 → 동의어들
    for syn in _REVERSE_SYNONYMS.get(lower, set()):
        forms.add(_normalize_for_index(syn))
    for syn in _REVERSE_SYNONYMS.get(normalized, set()):
        forms.add(_normalize_for_index(syn))
    return forms


class ReferenceIndex:
    """역색인 기반 레퍼런스 레시피 매칭 (서버 수명 동안 메모리 상주, ~1-2MB)"""

    def __init__(self):
        self._recipes: dict[int, dict] = {}
        self._ing_to_ids: dict[str, set[int]] = {}
        self._cat_ing_to_ids: dict[tuple[str, str], set[int]] = {}
        self._loaded = False

    def load(self):
        """DB에서 레퍼런스 레시피 전체 로드 → 역색인 빌드 (서버 시작 시 1회)"""
        self._recipes.clear()
        self._ing_to_ids.clear()
        self._cat_ing_to_ids.clear()

        rows = []
        try:
            from app.core.database import SessionLocal
            from app.models.reference_recipe import ReferenceRecipe

            db = SessionLocal()
            rows = db.query(ReferenceRecipe).all()
            db.close()
        except Exception as e:
            logger.warning(f"DB 레퍼런스 로드 실패, 하드코딩 폴백: {e}")

        if rows:
            for row in rows:
                self._index_recipe(row.id, {
                    "title": row.title,
                    "category": row.category,
                    "key_ingredients": row.key_ingredients or [],
                    "technique": row.technique,
                    "source": row.source,
                    "view_count": row.view_count or 0,
                })
            logger.info(
                f"레퍼런스 역색인 빌드 완료: {len(self._recipes)}개 레시피, "
                f"{len(self._ing_to_ids)}개 재료 키"
            )
        else:
            try:
                from app.data.reference_recipes import REFERENCE_RECIPES
            except ImportError:
                logger.warning("하드코딩 레퍼런스 파일 없음, 빈 인덱스로 시작")
                self._loaded = True
                return

            for i, r in enumerate(REFERENCE_RECIPES):
                self._index_recipe(-(i + 1), r)
            logger.info(f"레퍼런스 하드코딩 폴백 인덱스: {len(self._recipes)}개")

        self._loaded = True

    def _index_recipe(self, rid: int, recipe: dict):
        """단일 레시피를 역색인에 추가"""
        self._recipes[rid] = recipe
        cat = recipe.get("category", "")
        for ing in recipe.get("key_ingredients", []):
            for form in _all_forms(ing):
                self._ing_to_ids.setdefault(form, set()).add(rid)
                self._cat_ing_to_ids.setdefault((cat, form), set()).add(rid)

    def match_by_category(
        self,
        category: str,
        ingredients: list[str],
        exclude: list[str] | None = None,
        top_n: int = 3,
    ) -> list[dict]:
        """카테고리+재료로 역색인 매칭 (O(m) dict 룩업)"""
        if not self._loaded:
            self.load()
        if not self._recipes:
            return []

        exclude_lower = {e.strip().lower() for e in (exclude or [])}

        # O(m) 후보 수집: 각 user_ing당 최대 +1
        candidate_scores: dict[int, int] = {}
        for user_ing in ingredients:
            matched_ids: set[int] = set()
            for form in _all_forms(user_ing):
                matched_ids |= self._cat_ing_to_ids.get((category, form), set())
            for rid in matched_ids:
                candidate_scores[rid] = candidate_scores.get(rid, 0) + 1

        # 제외 필터 + 인기도 가중치
        scored: list[tuple[float, int]] = []
        for rid, match_count in candidate_scores.items():
            recipe = self._recipes[rid]
            key_ings = recipe.get("key_ingredients", [])
            if exclude_lower and any(
                ing.lower() in exclude_lower for ing in key_ings
            ):
                continue
            view_count = recipe.get("view_count", 0)
            view_bonus = math.log10(max(view_count, 1)) * 0.1 if view_count > 0 else 0
            score = match_count + view_bonus
            scored.append((score, rid))

        random.shuffle(scored)
        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {**self._recipes[rid], "_match_count": candidate_scores[rid], "_id": rid}
            for _, rid in scored[:top_n]
        ]


# 모듈 레벨 싱글톤
_index = ReferenceIndex()


# ── 카테고리별 매칭 함수 ──────────────────────────────────


def match_references_by_categories(
    categories: list[str],
    ingredients: list[str],
    exclude: list[str] | None = None,
) -> list[dict | None]:
    """카테고리별 1:1 레퍼런스 매칭 (중복 방지)"""
    used_ids: set[int] = set()
    results: list[dict | None] = []

    for cat in categories:
        matches = _index.match_by_category(cat, ingredients, exclude, top_n=3)
        found = None
        for m in matches:
            rid = m.get("_id")
            if rid not in used_ids:
                used_ids.add(rid)
                found = m
                break
        results.append(found)

    return results


def format_category_references(
    categories: list[str], methods: list[str], refs: list[dict | None]
) -> str:
    """카테고리 힌트 + 레퍼런스를 통합 포맷 (~80 토큰)"""
    lines = ["카테고리 배정 (각 레시피는 서로 다른 카테고리):"]
    for i, (cat, method, ref) in enumerate(zip(categories, methods, refs), 1):
        if ref and ref.get("_match_count", 0) >= 3:
            title = ref.get("title", "")
            technique = _summarize_technique(ref.get("technique", ""))
            lines.append(f"레시피 {i}: {cat} (참고: \"{title}\" - {technique})")
        elif ref:
            title = ref.get("title", "")
            lines.append(f"레시피 {i}: {cat} (참고: \"{title}\")")
        else:
            lines.append(f"레시피 {i}: {cat} 카테고리 ({method})")
    return "\n".join(lines)


def _summarize_technique(technique: str, max_len: int = 30) -> str:
    """기법 텍스트를 max_len자로 요약"""
    if not technique:
        return ""
    text = technique.strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    last_sep = max(cut.rfind(","), cut.rfind(" "))
    if last_sep > max_len // 2:
        return text[:last_sep].rstrip(",").strip()
    return text[:max_len].rstrip()


async def gather_references(
    ingredients: list[str],
    exclude: list[str] | None = None,
    *,
    categories: list[str],
    methods: list[str],
) -> str:
    """카테고리별 역색인 매칭 → 프롬프트용 텍스트 반환"""

    refs = match_references_by_categories(categories, ingredients, exclude)
    context = format_category_references(categories, methods, refs)

    if not context:
        return ""

    result = context
    result += "\n\n위 참고 레시피는 해당 카테고리에 어떤 요리가 있는지 보여주는 예시입니다. 그대로 따라하지 말고, 사용자 재료로 자유롭게 새 레시피를 만드세요."
    return result
