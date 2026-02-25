"""ingredient_validator.py 단위 테스트"""

import pytest

from app.services.ingredient_validator import (
    sanitize_ingredient,
    sanitize_ingredients,
    validate_ingredients,
)


class TestValidateIngredients:
    def test_valid_food_items(self):
        blocked = validate_ingredients(["김치", "계란", "양파", "돼지고기"])
        assert blocked == []

    def test_toxic_items_blocked(self):
        blocked = validate_ingredients(["독버섯", "김치"])
        assert "독버섯" in blocked
        assert "김치" not in blocked

    def test_chemical_items_blocked(self):
        blocked = validate_ingredients(["락스", "표백제"])
        assert len(blocked) == 2

    def test_metal_items_blocked(self):
        blocked = validate_ingredients(["납", "수은"])
        assert len(blocked) == 2

    def test_pattern_match_blocked(self):
        blocked = validate_ingredients(["화학물질", "살충제성분"])
        assert len(blocked) == 2

    def test_empty_list(self):
        blocked = validate_ingredients([])
        assert blocked == []

    def test_partial_match_blocked(self):
        """블록리스트 항목이 재료명에 부분적으로 포함된 경우도 차단"""
        blocked = validate_ingredients(["독버섯볶음"])
        assert len(blocked) == 1

    def test_whitespace_only_skipped(self):
        blocked = validate_ingredients(["  ", ""])
        assert blocked == []

    def test_case_insensitive(self):
        """영문 항목도 소문자로 변환하여 매칭"""
        blocked = validate_ingredients(["Paint"])
        # "paint"는 NON_FOOD_BLOCKLIST에 "페인트"로 있으므로
        # 영문 "paint"는 블록되지 않음 (한국어 블록리스트)
        assert blocked == []

    def test_multiple_blocked_returns_all(self):
        blocked = validate_ingredients(["독버섯", "납", "락스", "김치"])
        assert len(blocked) == 3
        assert "김치" not in blocked


class TestSanitizeIngredient:
    def test_basic_trim(self):
        assert sanitize_ingredient("  김치  ") == "김치"

    def test_special_chars_removed(self):
        result = sanitize_ingredient("김치!@#$%")
        assert result == "김치"

    def test_length_limit(self):
        long_name = "가" * 50
        result = sanitize_ingredient(long_name)
        assert len(result) == 30

    def test_allowed_chars_kept(self):
        """한글, 영문, 숫자, 하이픈, 괄호는 유지"""
        assert sanitize_ingredient("돼지고기(앞다리)") == "돼지고기(앞다리)"
        assert sanitize_ingredient("abc-123") == "abc-123"

    def test_whitespace_normalized(self):
        assert sanitize_ingredient("돼지   고기") == "돼지 고기"

    def test_empty_string(self):
        assert sanitize_ingredient("") == ""

    def test_only_special_chars(self):
        assert sanitize_ingredient("!@#$%") == ""


class TestSanitizeIngredients:
    def test_filters_empty_results(self):
        result = sanitize_ingredients(["김치", "!@#", "계란"])
        assert result == ["김치", "계란"]

    def test_all_valid(self):
        result = sanitize_ingredients(["김치", "계란", "양파"])
        assert result == ["김치", "계란", "양파"]

    def test_empty_list(self):
        assert sanitize_ingredients([]) == []
