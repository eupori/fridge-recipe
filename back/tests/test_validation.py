"""validation.py 단위 테스트"""

from datetime import datetime

import pytest

from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    Recipe,
)
from app.services.validation import (
    _auto_fix_missing_ingredients,
    _check_ingredient_step_consistency,
    _check_ingredient_usage_rate,
    _check_step_specificity,
    _check_style_diversity,
    validate_response,
)


def _make_recipe(**overrides) -> Recipe:
    defaults = {
        "title": "김치볶음밥",
        "summary": "간단한 김치볶음밥",
        "time_min": 10,
        "servings": 1,
        "ingredients_total": ["김치", "밥", "계란"],
        "ingredients_have": ["김치", "밥"],
        "ingredients_need": ["계란"],
        "steps": [
            "김치를 잘게 썬다",
            "팬에 기름을 두르고 김치를 3분간 볶는다",
            "밥을 넣고 중불에서 2분간 볶는다",
            "계란을 올리고 1분간 익힌다",
        ],
        "tips": ["찬밥이 더 맛있어요"],
    }
    defaults.update(overrides)
    return Recipe(**defaults)


def _make_request(**overrides) -> RecommendationCreate:
    defaults = {
        "ingredients": ["김치", "밥", "계란"],
        "constraints": {
            "time_limit_min": 15,
            "servings": 1,
            "tools": ["프라이팬"],
            "exclude": [],
        },
    }
    defaults.update(overrides)
    return RecommendationCreate(**defaults)


def _make_response(recipes=None, **overrides) -> RecommendationResponse:
    if recipes is None:
        recipes = [_make_recipe() for _ in range(3)]
    defaults = {
        "id": "rec_test123456",
        "created_at": datetime.now(),
        "recipes": recipes,
        "shopping_list": [],
    }
    defaults.update(overrides)
    return RecommendationResponse(**defaults)


class TestValidateResponse:
    def test_valid_response_passes(self):
        resp = _make_response()
        req = _make_request()
        validate_response(resp, req)  # 예외 없이 통과

    def test_wrong_recipe_count_fails(self):
        # Pydantic min_length=3 제약을 우회하기 위해 model_construct 사용
        resp = RecommendationResponse.model_construct(
            id="rec_test123456",
            created_at=datetime.now(),
            recipes=[_make_recipe(), _make_recipe()],
            shopping_list=[],
        )
        req = _make_request()
        with pytest.raises(ValueError, match="recipes_must_be_3"):
            validate_response(resp, req)

    def test_time_limit_exceeded_fails(self):
        resp = _make_response(
            recipes=[
                _make_recipe(time_min=20),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        with pytest.raises(ValueError, match="time_limit_exceeded"):
            validate_response(resp, req)

    def test_exclude_ingredient_detected(self):
        resp = _make_response()
        req = _make_request()
        req.constraints.exclude = ["김치"]
        with pytest.raises(ValueError, match="exclude_ingredient_detected"):
            validate_response(resp, req)

    def test_exclude_with_allergen_derivatives(self):
        """제외 재료의 파생 재료도 감지되는지 확인 (예: 우유 → 치즈)"""
        resp = _make_response(
            recipes=[
                _make_recipe(
                    title="치즈토스트",
                    ingredients_total=["빵", "치즈"],
                    ingredients_have=["빵"],
                    ingredients_need=["치즈"],
                    steps=[
                        "빵을 준비한다",
                        "치즈를 올린다",
                        "오븐에서 3분간 굽는다",
                        "접시에 담는다",
                    ],
                ),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        req.constraints.exclude = ["우유"]  # 우유 → 치즈 파생
        with pytest.raises(ValueError, match="exclude_ingredient_detected"):
            validate_response(resp, req)

    def test_steps_too_few_fails(self):
        resp = _make_response(
            recipes=[
                _make_recipe(steps=["1단계", "2단계", "3단계"]),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        with pytest.raises(ValueError, match="steps_length_invalid"):
            validate_response(resp, req)

    def test_steps_too_many_fails(self):
        resp = _make_response(
            recipes=[
                _make_recipe(steps=[f"{i}단계" for i in range(11)]),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        with pytest.raises(ValueError, match="steps_length_invalid"):
            validate_response(resp, req)

    def test_steps_boundary_4_passes(self):
        """4개 스텝은 유효"""
        resp = _make_response(
            recipes=[
                _make_recipe(
                    steps=[
                        "김치를 썬다",
                        "팬에 김치를 3분간 볶는다",
                        "밥을 넣고 볶는다",
                        "계란을 올린다",
                    ]
                ),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        validate_response(resp, req)

    def test_steps_boundary_10_passes(self):
        """10개 스텝은 유효"""
        steps_10 = [
            "김치를 잘게 썬다",
            "팬에 기름을 두른다",
            "김치를 3분간 볶는다",
            "밥을 넣는다",
            "중불에서 2분간 볶는다",
            "계란을 풀어 넣는다",
            "1분간 더 볶는다",
            "참기름을 넣는다",
            "접시에 담는다",
            "깨를 뿌린다",
        ]
        resp = _make_response(
            recipes=[
                _make_recipe(steps=steps_10),
                _make_recipe(),
                _make_recipe(),
            ]
        )
        req = _make_request()
        validate_response(resp, req)


class TestIngredientStepConsistency:
    def test_title_ingredient_in_steps(self):
        missing = _check_ingredient_step_consistency(
            "김치볶음밥", ["김치", "밥"], ["김치를 볶는다", "밥을 넣는다"]
        )
        assert missing == []

    def test_title_ingredient_missing_from_steps(self):
        missing = _check_ingredient_step_consistency(
            "김치볶음밥", ["김치", "밥"], ["재료를 볶는다"]
        )
        assert "김치" in missing

    def test_implicit_ingredients_skipped(self):
        """_IMPLICIT_INGREDIENTS(소금, 기름 등)는 체크하지 않음"""
        missing = _check_ingredient_step_consistency(
            "소금밥", ["소금", "밥"], ["밥을 짓는다"]
        )
        # 소금은 _IMPLICIT_INGREDIENTS → 스킵, 밥은 제목에 있고 steps에 있음
        assert "소금" not in missing

    def test_ingredient_not_in_title_skipped(self):
        """제목에 없는 재료는 체크하지 않음"""
        missing = _check_ingredient_step_consistency(
            "김치볶음밥", ["김치", "당근"], ["김치를 볶는다"]
        )
        # 당근은 제목에 없으므로 체크 안 함
        assert "당근" not in missing

    def test_empty_inputs(self):
        assert _check_ingredient_step_consistency("", [], []) == []


class TestAutoFixMissingIngredients:
    def test_replaces_generic_ingredient_reference(self):
        recipe = _make_recipe(
            title="김치볶음밥",
            ingredients_total=["김치", "밥"],
            steps=["재료를 준비한다", "재료를 넣고 볶는다", "접시에 담는다", "완성한다"],
        )
        _auto_fix_missing_ingredients(recipe, ["김치"])
        joined = " ".join(recipe.steps)
        assert "김치" in joined

    def test_inserts_step_when_no_generic_reference(self):
        recipe = _make_recipe(
            title="김치볶음밥",
            ingredients_total=["김치", "밥"],
            steps=["밥을 준비한다", "팬을 달군다", "볶는다", "완성한다"],
        )
        _auto_fix_missing_ingredients(recipe, ["김치"])
        joined = " ".join(recipe.steps)
        assert "김치" in joined

    def test_no_change_when_no_missing(self):
        recipe = _make_recipe()
        original_steps = list(recipe.steps)
        _auto_fix_missing_ingredients(recipe, [])
        assert recipe.steps == original_steps


class TestIngredientUsageRate:
    def test_all_ingredients_mentioned(self):
        recipe = _make_recipe(
            ingredients_total=["김치", "밥"],
            steps=["김치를 볶는다", "밥을 넣는다"],
        )
        assert _check_ingredient_usage_rate(recipe) == 1.0

    def test_some_ingredients_missing(self):
        recipe = _make_recipe(
            ingredients_total=["김치", "밥", "당근", "양파"],
            steps=["김치를 볶는다", "밥을 넣는다"],
        )
        assert _check_ingredient_usage_rate(recipe) == 0.5

    def test_implicit_ingredients_excluded(self):
        """소금, 기름 등 암묵적 재료는 사용률 계산에서 제외"""
        recipe = _make_recipe(
            ingredients_total=["김치", "소금", "기름"],
            steps=["김치를 볶는다"],
        )
        # 소금, 기름은 _IMPLICIT → 제외, 김치만 카운트 → 1/1 = 1.0
        assert _check_ingredient_usage_rate(recipe) == 1.0

    def test_empty_total_returns_one(self):
        recipe = _make_recipe(ingredients_total=[])
        assert _check_ingredient_usage_rate(recipe) == 1.0


class TestCheckStepSpecificity:
    def test_specific_steps(self):
        steps = [
            "중불에서 3분간 볶는다",
            "약불로 줄이고 5분간 끓인다",
            "노릇해질 때까지 굽는다",
            "2분간 더 익힌다",
        ]
        spec = _check_step_specificity(steps)
        assert spec["time_ratio"] >= 0.5
        assert spec["heat_ratio"] > 0.0
        assert spec["state_ratio"] > 0.0

    def test_vague_steps(self):
        steps = ["볶는다", "넣는다", "섞는다", "완성한다"]
        spec = _check_step_specificity(steps)
        assert spec["time_ratio"] == 0.0
        assert spec["heat_ratio"] == 0.0
        assert spec["state_ratio"] == 0.0

    def test_empty_steps(self):
        spec = _check_step_specificity([])
        assert spec == {"time_ratio": 0.0, "heat_ratio": 0.0, "state_ratio": 0.0}


class TestStyleDiversity:
    def test_diverse_styles(self):
        r1 = _make_recipe(title="김치볶음밥", steps=["밥을 볶는다"])
        r2 = _make_recipe(title="된장찌개", steps=["된장을 끓인다"])
        r3 = _make_recipe(title="계란전", steps=["계란을 부친다"])
        assert _check_style_diversity([r1, r2, r3]) is True

    def test_same_style(self):
        r1 = _make_recipe(title="김치볶음밥", steps=["밥을 볶는다"])
        r2 = _make_recipe(title="새우볶음밥", steps=["밥을 볶는다"])
        r3 = _make_recipe(title="참치볶음밥", steps=["밥을 볶는다"])
        assert _check_style_diversity([r1, r2, r3]) is False

    def test_single_recipe(self):
        r1 = _make_recipe(title="김치볶음밥")
        assert _check_style_diversity([r1]) is True

    def test_partial_overlap_is_diverse(self):
        """일부 스타일만 겹치면 다양한 것으로 판단"""
        r1 = _make_recipe(title="볶음밥", steps=["밥을 볶는다"])  # {볶음, 밥}
        r2 = _make_recipe(title="볶음면", steps=["면을 볶는다"])  # {볶음, 면}
        r3 = _make_recipe(title="볶음전", steps=["전을 볶는다"])  # {볶음, 전}
        # common = {볶음}, all = {볶음, 밥, 면, 전} → all != common → True
        assert _check_style_diversity([r1, r2, r3]) is True
