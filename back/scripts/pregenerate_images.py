"""
주요 한국 요리 이미지 사전 생성 스크립트

Gemini API로 자주 등장하는 요리 이미지를 미리 생성하여 캐시에 저장합니다.
이후 레시피 생성 시 퍼지 매칭으로 캐시된 이미지를 재사용하여 API 비용을 절감합니다.

사용법 (EC2 서버):
    docker compose exec -T api python scripts/pregenerate_images.py

사용법 (로컬):
    cd back && PYTHONPATH=. python scripts/pregenerate_images.py

비용: ~40개 × $0.039 = ~$1.56 (1회성)
"""

import asyncio
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.image_search_service import ImageSearchService, KOREAN_FOOD_TRANSLATIONS


# 사전 생성할 요리 목록 (KOREAN_FOOD_TRANSLATIONS 전체 + 추가)
DISHES_TO_GENERATE = list(KOREAN_FOOD_TRANSLATIONS.keys()) + [
    "카레", "오므라이스", "돈까스", "치킨", "토스트",
]


async def main():
    service = ImageSearchService()

    already_cached = 0
    generated = 0
    failed = 0
    skipped_dishes = []

    print(f"=== 이미지 사전 생성 시작 ===")
    print(f"대상: {len(DISHES_TO_GENERATE)}개 요리")
    print(f"현재 캐시: {len(service.cache)}개 항목")
    print()

    for i, dish in enumerate(DISHES_TO_GENERATE, 1):
        # 이미 캐시에 있으면 스킵
        if dish in service.cache:
            cached_url = service.cache[dish].get("url")
            if cached_url:
                already_cached += 1
                print(f"  [{i}/{len(DISHES_TO_GENERATE)}] ✓ 캐시 존재: {dish}")
                continue

        # 퍼지 매칭으로도 이미 있으면 스킵
        fuzzy_url = service._fuzzy_cache_lookup(dish)
        if fuzzy_url:
            already_cached += 1
            print(f"  [{i}/{len(DISHES_TO_GENERATE)}] ≈ 퍼지 캐시: {dish}")
            continue

        print(f"  [{i}/{len(DISHES_TO_GENERATE)}] ⏳ 생성 중: {dish}...", end="", flush=True)

        try:
            url = await service.get_image(dish)
            if url:
                generated += 1
                print(f" ✓ 완료")
            else:
                failed += 1
                skipped_dishes.append(dish)
                print(f" ✗ 실패")
        except Exception as e:
            failed += 1
            skipped_dishes.append(dish)
            print(f" ✗ 에러: {e}")

        # Rate limiting: Gemini API 과부하 방지
        if generated % 5 == 0 and generated > 0:
            print(f"    (5개 생성 완료, 10초 대기...)")
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(2)

    print()
    print(f"=== 결과 ===")
    print(f"  이미 캐시됨: {already_cached}개")
    print(f"  새로 생성:   {generated}개")
    print(f"  실패:        {failed}개")
    print(f"  총 캐시:     {len(service.cache)}개")

    if skipped_dishes:
        print(f"\n  실패 목록: {', '.join(skipped_dishes)}")

    # 예상 비용 출력
    cost = generated * 0.039
    print(f"\n  예상 비용: ${cost:.2f} (약 {int(cost * 1350)}원)")


if __name__ == "__main__":
    asyncio.run(main())
