"""
이미지 검색 서비스 테스트 스크립트

Google Custom Search API 통합을 테스트합니다.

실행 방법:
1. Mock 모드 (API 키 불필요):
   IMAGE_SEARCH_PROVIDER=mock python test_image_search.py

2. Unsplash 모드:
   IMAGE_SEARCH_PROVIDER=unsplash python test_image_search.py

3. Google API 모드:
   IMAGE_SEARCH_PROVIDER=google \
   GOOGLE_API_KEY=your-key \
   GOOGLE_SEARCH_ENGINE_ID=your-cx \
   python test_image_search.py
"""

import asyncio
import sys
import time
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.services.image_search_service import ImageSearchService

# 테스트용 한국 음식 목록
TEST_RECIPES = [
    "김치볶음밥",
    "된장찌개",
    "불고기",
    "비빔밥",
    "계란말이",
]


async def test_basic_search():
    """기본 이미지 검색 테스트"""
    print("\n" + "=" * 60)
    print("테스트 1: 기본 이미지 검색")
    print("=" * 60)
    print(f"Provider: {settings.image_search_provider}")
    print(f"Cache: {settings.image_cache_enabled}")
    print()

    service = ImageSearchService()

    for recipe in TEST_RECIPES:
        print(f"🔍 검색 중: {recipe}")
        start_time = time.time()

        image_url = await service.get_image(recipe)
        elapsed = time.time() - start_time

        if image_url:
            print(f"  ✅ 성공 ({elapsed:.2f}초): {image_url[:80]}...")
        else:
            print(f"  ❌ 실패 ({elapsed:.2f}초)")
        print()

    return service


async def test_cache_performance(service: ImageSearchService):
    """캐시 성능 테스트"""
    print("\n" + "=" * 60)
    print("테스트 2: 캐시 성능 테스트")
    print("=" * 60)

    if not settings.image_cache_enabled:
        print("⚠️ 캐시가 비활성화되어 있습니다. 테스트 건너뜀.")
        return

    # 첫 번째 검색 (캐시 미스)
    recipe = TEST_RECIPES[0]
    print(f"첫 번째 검색 (캐시 미스): {recipe}")
    start_time = time.time()
    result1 = await service.get_image(recipe)
    elapsed1 = time.time() - start_time
    print(f"  시간: {elapsed1:.3f}초")
    print(f"  결과: {result1[:80] if result1 else 'None'}...")
    print()

    # 두 번째 검색 (캐시 히트)
    print(f"두 번째 검색 (캐시 히트): {recipe}")
    start_time = time.time()
    result2 = await service.get_image(recipe)
    elapsed2 = time.time() - start_time
    print(f"  시간: {elapsed2:.3f}초")
    print(f"  결과: {result2[:80] if result2 else 'None'}...")
    print()

    # 성능 비교
    if elapsed2 < elapsed1:
        speedup = elapsed1 / elapsed2
        print(f"✅ 캐시 히트로 {speedup:.1f}x 빠름")
    else:
        print("⚠️ 캐시 성능 개선 없음")

    # 캐시 통계
    stats = service.get_cache_stats()
    print(f"\n캐시 통계: {stats}")


async def test_parallel_search():
    """병렬 검색 성능 테스트"""
    print("\n" + "=" * 60)
    print("테스트 3: 병렬 검색 성능 (3개 레시피 동시)")
    print("=" * 60)

    service = ImageSearchService()

    # 순차 검색
    print("순차 검색:")
    start_time = time.time()
    sequential_results = []
    for recipe in TEST_RECIPES[:3]:
        result = await service.get_image(recipe)
        sequential_results.append(result)
    sequential_time = time.time() - start_time
    print(f"  시간: {sequential_time:.2f}초")
    print(f"  성공: {sum(1 for r in sequential_results if r)}개")
    print()

    # 캐시 초기화
    service.clear_cache()

    # 병렬 검색
    print("병렬 검색:")
    start_time = time.time()
    tasks = [service.get_image(recipe) for recipe in TEST_RECIPES[:3]]
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    parallel_time = time.time() - start_time

    successful = sum(1 for r in parallel_results if r and not isinstance(r, Exception))
    print(f"  시간: {parallel_time:.2f}초")
    print(f"  성공: {successful}개")
    print()

    # 성능 비교
    if parallel_time < sequential_time:
        speedup = sequential_time / parallel_time
        print(f"✅ 병렬 처리로 {speedup:.1f}x 빠름")
    else:
        print("⚠️ 병렬 처리 성능 개선 없음 (캐시 또는 네트워크 제약)")


async def test_fallback():
    """폴백 동작 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: 폴백 동작 확인")
    print("=" * 60)

    # 존재하지 않는 음식명으로 테스트
    fake_recipe = "존재하지않는음식명12345xyz"
    print(f"검색: {fake_recipe}")

    service = ImageSearchService()
    result = await service.get_image(fake_recipe)

    if result:
        print(f"  ✅ Fallback 성공: {result[:80]}...")
        if "unsplash" in result:
            print("  → Unsplash로 폴백됨")
        elif "placeholder" in result:
            print("  → Mock 이미지 사용됨")
    else:
        print("  ❌ 모든 provider 실패")


async def test_korean_translation():
    """한국어 번역 매핑 테스트"""
    print("\n" + "=" * 60)
    print("테스트 5: 한국어-영어 번역 매핑")
    print("=" * 60)

    from app.services.image_search_service import KOREAN_FOOD_TRANSLATIONS, GoogleImageSearchAdapter

    adapter = GoogleImageSearchAdapter()

    test_cases = [
        ("김치볶음밥", "매핑 있음"),
        ("간단한 김치볶음밥", "부분 매칭"),
        ("알 수 없는 요리", "매핑 없음"),
    ]

    for query, description in test_cases:
        enhanced = adapter._enhance_korean_query(query)
        english_only = adapter._get_english_translation(query)

        print(f"\n쿼리: {query} ({description})")
        print(f"  증강 쿼리: {enhanced}")
        print(f"  영어 전용: {english_only}")

    print(f"\n총 {len(KOREAN_FOOD_TRANSLATIONS)}개 음식 매핑 등록됨")


async def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 70)
    print("🍳 Fridge-Recipe 이미지 검색 서비스 테스트")
    print("=" * 70)

    print("\n환경 설정:")
    print(f"  IMAGE_SEARCH_PROVIDER: {settings.image_search_provider}")
    print(f"  IMAGE_CACHE_ENABLED: {settings.image_cache_enabled}")
    print(f"  IMAGE_SEARCH_TIMEOUT: {settings.image_search_timeout}초")

    if settings.image_search_provider == "google":
        if settings.google_api_key:
            print(f"  GOOGLE_API_KEY: {settings.google_api_key[:20]}...")
        else:
            print("  ⚠️ GOOGLE_API_KEY 미설정")

        if settings.google_search_engine_id:
            print(f"  GOOGLE_SEARCH_ENGINE_ID: {settings.google_search_engine_id[:20]}...")
        else:
            print("  ⚠️ GOOGLE_SEARCH_ENGINE_ID 미설정")

    try:
        # 테스트 실행
        service = await test_basic_search()
        await test_cache_performance(service)
        await test_parallel_search()
        await test_fallback()
        await test_korean_translation()

        print("\n" + "=" * 70)
        print("✅ 모든 테스트 완료!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
