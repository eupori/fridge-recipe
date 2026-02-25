# Multi-domain Recipe Crawl

`crawl_multi_domain.py`는 여러 레시피 사이트 + YouTube에서 레시피를 추출해서 아래 JSONL 스키마로 저장합니다.

## 출력 포맷

```json
{
  "title": "김치찌개",
  "category": "국물",
  "key_ingredients": ["김치", "돼지고기", "두부"],
  "all_ingredients": ["김치 200g", "돼지고기 150g", "두부 1/2모", "대파 1대"],
  "steps": ["김치를 볶는다", "물을 넣고 끓인다"],
  "technique": "중불에서 10분 끓이기",
  "time_min": 15,
  "servings": 2,
  "source": "만개의레시피",
  "source_url": "https://example.com/recipe/123",
  "view_count": 50000,
  "rating": 45
}
```

## 지원 도메인 키

- `10000recipe`
- `allrecipes`
- `maangchi`
- `mykoreankitchen`
- `koreanbapsang`
- `seriouseats`

## 실행 예시

```bash
cd back

# 1) 다중 도메인 수집 (도메인별 최대 300)
PYTHONPATH=. python scripts/crawl_multi_domain.py \
  --domains allrecipes,maangchi,mykoreankitchen,koreanbapsang \
  --per-domain 300 \
  --output data/reference_recipes_batch1.jsonl

# 2) YouTube 포함
# 환경변수 필요: YOUTUBE_API_KEY
PYTHONPATH=. python scripts/crawl_multi_domain.py \
  --domains maangchi,mykoreankitchen \
  --per-domain 200 \
  --youtube \
  --youtube-max-per-channel 40 \
  --output data/reference_recipes_with_youtube.jsonl
```

## DB 임포트

생성된 JSONL은 기존 임포터로 바로 넣을 수 있습니다.

```bash
cd back
PYTHONPATH=. python scripts/import_recipes.py data/reference_recipes_with_youtube.jsonl
```

## 참고

- 사이트별 구조 차이는 JSON-LD Recipe 파싱으로 흡수합니다.
- URL 중복은 `source_url` 기준으로 제거합니다.
- 레시피 중복(의미 중복)까지 강하게 막으려면 임포트 전에 유사도 필터를 추가하는 것이 좋습니다.
