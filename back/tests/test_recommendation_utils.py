"""
recommendation_service.py 순수 함수 테스트

- normalize_ingredient(): 분량/수식어 제거
- deduplicate_shopping_list(): 정규화 후 중복 제거
- split_have_need(): 퍼지 매칭으로 보유/필요 분리
"""

import pytest

from app.services.recommendation_service import (
    deduplicate_shopping_list,
    normalize_ingredient,
    split_have_need,
)


# ---- normalize_ingredient ----


class TestNormalizeIngredient:
    def test_removes_quantity_with_unit(self):
        assert normalize_ingredient("계란 2개") == "계란"

    def test_removes_weight(self):
        assert normalize_ingredient("김치 100g") == "김치"

    def test_removes_volume(self):
        assert normalize_ingredient("우유 200ml") == "우유"

    def test_removes_spoon_unit(self):
        assert normalize_ingredient("간장 1큰술") == "간장"

    def test_removes_fraction(self):
        assert normalize_ingredient("양파 1/2개") == "양파"

    def test_removes_modifier_fresh(self):
        assert normalize_ingredient("신선한 계란") == "계란"

    def test_removes_modifier_chopped(self):
        assert normalize_ingredient("다진 마늘") == "마늘"

    def test_removes_modifier_frozen(self):
        assert normalize_ingredient("냉동 만두") == "만두"

    def test_removes_modifier_blanched(self):
        assert normalize_ingredient("데친 시금치") == "시금치"

    def test_removes_modifier_boiled(self):
        assert normalize_ingredient("삶은 달걀") == "달걀"

    def test_combined_modifier_and_quantity(self):
        assert normalize_ingredient("신선한 계란 1개") == "계란"

    def test_empty_string(self):
        assert normalize_ingredient("") == ""

    def test_only_ingredient_name(self):
        assert normalize_ingredient("김치") == "김치"

    def test_whitespace_handling(self):
        assert normalize_ingredient("  계란  ") == "계란"

    def test_removes_approximate_quantity(self):
        assert normalize_ingredient("적당량 소금") == "소금"

    def test_removes_slightly(self):
        assert normalize_ingredient("약간 후추") == "후추"


# ---- deduplicate_shopping_list ----


class TestDeduplicateShoppingList:
    def test_removes_duplicates_with_quantities(self):
        result = deduplicate_shopping_list({"계란 1개", "계란 2개"})
        assert result == ["계란"]

    def test_preserves_unique_items(self):
        result = deduplicate_shopping_list({"김치", "계란", "밥"})
        assert sorted(result) == ["계란", "김치", "밥"]

    def test_empty_set(self):
        assert deduplicate_shopping_list(set()) == []

    def test_single_item(self):
        assert deduplicate_shopping_list({"김치"}) == ["김치"]

    def test_sorted_output(self):
        result = deduplicate_shopping_list({"파", "김치", "계란"})
        assert result == sorted(result)


# ---- split_have_need ----


class TestSplitHaveNeed:
    def test_exact_match(self):
        have, need = split_have_need(["김치", "밥"], ["김치", "밥", "계란"])
        assert "김치" in have
        assert "밥" in have
        assert "계란" in need

    def test_fuzzy_match_with_quantity(self):
        """LLM이 '계란 2개' 반환해도 사용자의 '계란'과 매칭"""
        have, need = split_have_need(["계란"], ["계란 2개", "소금"])
        assert "계란 2개" in have
        assert "소금" in need

    def test_partial_match_substring(self):
        """부분 문자열 매칭 (대파 ⊃ 파)"""
        have, need = split_have_need(["대파"], ["파", "소금"])
        assert "파" in have

    def test_case_insensitive(self):
        have, need = split_have_need(["Egg"], ["egg", "sugar"])
        assert "egg" in have

    def test_empty_user_ingredients(self):
        have, need = split_have_need([], ["김치", "밥"])
        assert have == []
        assert sorted(need) == ["김치", "밥"]

    def test_all_ingredients_matched(self):
        have, need = split_have_need(["김치", "밥", "계란"], ["김치", "밥", "계란"])
        assert len(need) == 0
        assert sorted(have) == ["계란", "김치", "밥"]

    def test_empty_recipe_ingredients(self):
        have, need = split_have_need(["김치"], [])
        assert have == []
        assert need == []
