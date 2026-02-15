# Deep Review Results

## Review Information
- **Branch**: master
- **Review Date**: 2026-02-15
- **Review Method**: 4 persona parallel review + discussion
- **Personas**: User Advocate, CTO, Senior Dev, AI Auditor (Peer Dev excluded - structural review prioritized)

## Files Reviewed
- `back/app/core/config.py`
- `back/app/models/recommendation.py`
- `back/app/services/image_search_service.py`
- `back/app/services/youtube_video_service.py` (new)
- `back/app/services/recommendation_service.py`
- `back/requirements.txt`
- `front/app/page.tsx`
- `front/app/r/[id]/ResultClient.tsx`
- `front/types/recommendation.ts`

## Expert Scores
| Perspective | Score | Assessment |
|-------------|-------|------------|
| User Advocate | 6/10 | Silent degradation, promise vs delivery gap |
| CTO | 7/10 | Gemini model wrong, YouTube quota risk |
| Senior Dev | 7/10 | Code duplication, deprecated async API |
| AI Auditor | 5/10 | Critical model issue, cache collision |
| **Overall** | **6.25/10** | |

## Required Fixes (Priority 1)

### 1. [Critical] config.py:59 — Wrong Gemini model for image generation
- **Issue**: `gemini-2.5-flash-preview-05-20` is a text/reasoning model, NOT an image generation model. Detailed mode images fail 100% silently.
- **Suggestion**: Use same model (`gemini-2.0-flash-exp-image-generation`) with enhanced prompt instead, or validate model supports image generation.
- **Agreed by**: CTO, AI Auditor

### 2. [High] recommendation_service.py:313-319 — Timeout discards ALL partial results
- **Issue**: `asyncio.wait_for(asyncio.gather(...))` on timeout replaces all results with None, even if images finished before YouTube timed out.
- **Suggestion**: Use individual task wrapping to preserve partial results on timeout.
- **Agreed by**: User Advocate, CTO, Senior Dev, AI Auditor

## Required Fixes (Priority 2)

### 3. [High] image_search_service.py:608 — Deprecated asyncio API
- **Issue**: `asyncio.get_event_loop()` deprecated since Python 3.10, will break on 3.12+.
- **Suggestion**: Replace with `asyncio.get_running_loop()`.
- **Agreed by**: CTO, Senior Dev

### 4. [High] image_search_service.py cache — Quality-level cache collision
- **Issue**: Cache key uses bare `recipe_title` without quality_level. Standard images served for detailed requests.
- **Suggestion**: Include quality_level in cache key.
- **Agreed by**: CTO, AI Auditor

### 5. [High] recommendation_service.py:303-332 — Broad exception handling masks bugs
- **Issue**: Lazy import with `except Exception` catches all errors including syntax errors in youtube_video_service.py.
- **Suggestion**: Catch only `ImportError` for lazy import, handle others separately.
- **Agreed by**: Senior Dev, AI Auditor

### 6. [High] recommendation_service.py:291 — Untyped variable
- **Issue**: `video_results: list` lacks type hint.
- **Suggestion**: Use `list[ReferenceVideo | None]`.
- **Agreed by**: Senior Dev

## Recommended Fixes (Priority 3)

### 7. [Medium] page.tsx:396 — Promise vs delivery gap
- **Issue**: "참고 영상까지 포함해요" but videos not guaranteed (quota, API failures).
- **Suggestion**: Soften to conditional language.
- **Agreed by**: User Advocate

### 8. [Medium] youtube_video_service.py:149 — viewCount crash risk
- **Issue**: `int(stats.get('viewCount', 0))` can crash on non-numeric strings.
- **Suggestion**: Add defensive parsing with try/except.
- **Agreed by**: AI Auditor

### 9. [Medium] image_search_service.py FOOD_ANGLE_MAP — Matching order
- **Issue**: Generic "밥" matches before specific "볶음밥" due to dict iteration order.
- **Suggestion**: Match by longest keyword first.
- **Agreed by**: AI Auditor

### 10. [Medium] Code duplication — youtube_adapter.py vs youtube_video_service.py
- **Issue**: Constants, API calls, ranking logic duplicated.
- **Suggestion**: Extract shared YouTube API client. (Future improvement)
- **Agreed by**: Senior Dev

## Discussion Results
| Topic | Conclusion |
|-------|------------|
| YouTube API quota (~33 req/day) | HIGH risk - needs monitoring + circuit breaker (future) |
| Sync LLM calls blocking event loop | Accepted for current scale, future improvement |
| Google Images scraping ToS | Low priority - Gemini is default provider, scraping is legacy |
| YouTube link domain | Not actionable - youtube.com works fine |

## Action Items
- [x] Fix Priority 1: Gemini model → image generation 지원 모델로 수정
- [x] Fix Priority 1: asyncio.gather 타임아웃 시 부분 결과 보존 (개별 wait_for 래핑)
- [x] Fix Priority 2: asyncio.get_event_loop() → get_running_loop()
- [x] Fix Priority 2: 이미지 캐시 키에 quality_level 포함
- [x] Fix Priority 2: YouTube import except 범위 좁힘 (ImportError만)
- [x] Fix Priority 2: video_results 타입 힌트 추가
- [x] Fix Priority 3: viewCount 방어적 파싱
- [x] Fix Priority 3: FOOD_ANGLE_MAP 긴 키워드 우선 매칭
- [x] Fix Priority 3: 정밀 모드 설명 텍스트 정확도 개선
- [x] Add YouTube API quota monitoring → YouTubeQuotaTracker circuit breaker 구현 (youtube_client.py)
- [x] Extract shared YouTube client → YouTubeAPIClient 공유 클라이언트로 리팩토링 완료
