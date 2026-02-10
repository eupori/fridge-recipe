"""
LLM 통합 테스트 스크립트

Usage:
    # Mock 모드 (API 키 불필요)
    LLM_PROVIDER=mock python test_llm_integration.py

    # 실제 Claude API 사용
    ANTHROPIC_API_KEY=sk-ant-... python test_llm_integration.py
"""

import asyncio
import os
import sys

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.recommendation import Constraints, RecommendationCreate
from app.services.recommendation_service import create_recommendation


async def test_basic_recipe_generation():
    """기본 레시피 생성 테스트"""
    print("=" * 60)
    print("LLM 통합 테스트 시작")
    print("=" * 60)
    print(f"Provider: {settings.llm_provider}")
    print(f"Model: {settings.llm_model}")
    print()

    # 테스트 입력
    payload = RecommendationCreate(
        ingredients=["계란", "김치", "양파", "밥"],
        constraints=Constraints(
            time_limit_min=15, servings=1, tools=["프라이팬", "전자레인지"], exclude=["우유"]
        ),
    )

    print("입력 재료:", ", ".join(payload.ingredients))
    print("시간 제한:", payload.constraints.time_limit_min, "분")
    print("제외 재료:", ", ".join(payload.constraints.exclude) or "없음")
    print()

    try:
        # 레시피 생성
        print("레시피 생성 중...")
        response = await create_recommendation(payload)

        # 결과 출력
        print("\n" + "=" * 60)
        print(f"✅ 레시피 생성 성공! (ID: {response.id})")
        print("=" * 60)

        for i, recipe in enumerate(response.recipes, 1):
            print(f"\n[레시피 {i}] {recipe.title}")
            print(f"  조리 시간: {recipe.time_min}분")
            print(f"  인분: {recipe.servings}인분")
            print(f"  요약: {recipe.summary}")
            print(
                f"  전체 재료 ({len(recipe.ingredients_total)}개): {', '.join(recipe.ingredients_total)}"
            )
            print(
                f"  보유 재료 ({len(recipe.ingredients_have)}개): {', '.join(recipe.ingredients_have) or '없음'}"
            )
            print(
                f"  필요 재료 ({len(recipe.ingredients_need)}개): {', '.join(recipe.ingredients_need) or '없음'}"
            )
            print(f"  조리 단계 ({len(recipe.steps)}개):")
            for j, step in enumerate(recipe.steps, 1):
                print(f"    {j}. {step}")
            if recipe.tips:
                print(f"  팁: {', '.join(recipe.tips)}")

        print(f"\n장보기 리스트 ({len(response.shopping_list)}개):")
        if response.shopping_list:
            for item in response.shopping_list:
                print(f"  - {item.item}")
        else:
            print("  (모든 재료 보유)")

        print("\n" + "=" * 60)
        print("✅ 검증 통과!")
        print("=" * 60)

        return response

    except Exception as e:
        print(f"\n❌ 에러 발생: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


async def test_exclude_ingredients():
    """제외 재료 테스트"""
    print("\n\n" + "=" * 60)
    print("제외 재료 테스트")
    print("=" * 60)

    payload = RecommendationCreate(
        ingredients=["계란", "밥"],
        constraints=Constraints(time_limit_min=10, servings=1, exclude=["김치", "우유"]),
    )

    print("입력 재료:", ", ".join(payload.ingredients))
    print("제외 재료:", ", ".join(payload.constraints.exclude))
    print()

    try:
        response = await create_recommendation(payload)

        # 제외 재료 검증
        exclude_set = set(payload.constraints.exclude)
        for recipe in response.recipes:
            text_blob = " ".join(
                [
                    recipe.title,
                    recipe.summary,
                    " ".join(recipe.ingredients_total),
                    " ".join(recipe.steps),
                ]
            )

            for excluded in exclude_set:
                if excluded in text_blob:
                    print(f"❌ 제외 재료 '{excluded}'가 발견됨: {recipe.title}")
                    return False

        print("✅ 제외 재료 검증 통과!")
        return True

    except Exception as e:
        print(f"❌ 에러: {str(e)}")
        return False


async def test_time_limit():
    """시간 제한 테스트"""
    print("\n\n" + "=" * 60)
    print("시간 제한 테스트")
    print("=" * 60)

    payload = RecommendationCreate(
        ingredients=["계란", "밥"], constraints=Constraints(time_limit_min=10, servings=1)
    )

    print("시간 제한:", payload.constraints.time_limit_min, "분")
    print()

    try:
        response = await create_recommendation(payload)

        for recipe in response.recipes:
            if recipe.time_min > payload.constraints.time_limit_min:
                print(
                    f"❌ 시간 초과: {recipe.title} ({recipe.time_min}분 > {payload.constraints.time_limit_min}분)"
                )
                return False

        print("✅ 시간 제한 검증 통과!")
        return True

    except Exception as e:
        print(f"❌ 에러: {str(e)}")
        return False


async def main():
    """메인 테스트 함수"""
    print("\n현재 설정:")
    print(f"  LLM Provider: {settings.llm_provider}")
    print(f"  Model: {settings.llm_model}")
    print(f"  API Key: {'설정됨' if settings.anthropic_api_key else '미설정'}")
    print(f"  Image Search Provider: {settings.image_search_provider}")
    print()

    if settings.llm_provider == "anthropic" and not settings.anthropic_api_key:
        print("⚠️  ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        print("    Mock 모드로 테스트하려면: LLM_PROVIDER=mock python test_llm_integration.py")
        print(
            "    실제 API 사용하려면: ANTHROPIC_API_KEY=sk-ant-... python test_llm_integration.py"
        )
        sys.exit(1)

    # 테스트 실행
    await test_basic_recipe_generation()

    # 추가 테스트 (mock 모드에서는 건너뛰기)
    if settings.llm_provider != "mock":
        await test_exclude_ingredients()
        await test_time_limit()

    print("\n\n🎉 모든 테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
