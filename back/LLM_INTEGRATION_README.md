# LLM 통합 구현 완료 - Claude API 레시피 생성

## 구현 개요

하드코딩된 더미 데이터를 **Claude Sonnet 4.5 API**를 사용한 실제 레시피 생성으로 교체했습니다.

## 변경사항 요약

### 1. 새로 추가된 파일

- `back/app/services/llm_adapter.py` (약 340줄)
  - `RecipeLLMAdapter`: Claude API를 사용한 실제 레시피 생성
  - `MockRecipeLLMAdapter`: API 키 없이 테스트할 수 있는 Mock 구현
  - 재시도 로직, 에러 핸들링, 폴백 처리 포함

- `back/test_llm_integration.py` (약 180줄)
  - LLM 통합 테스트 스크립트
  - Mock 모드와 실제 API 모드 모두 지원

### 2. 수정된 파일

#### `back/requirements.txt`
```diff
+ anthropic==0.42.0
```

#### `back/app/core/config.py`
```python
# LLM 설정 업데이트
llm_provider: str = "anthropic"  # openai → anthropic
anthropic_api_key: str | None = None  # 추가
llm_model: str = "claude-sonnet-4-5-20250929"
llm_temperature: float = 0.7  # 추가
llm_max_tokens: int = 4000  # 추가
```

#### `back/app/services/recommendation_service.py`
- 40-109줄 더미 데이터 로직 완전 제거
- LLM 어댑터를 사용한 실제 레시피 생성 로직으로 교체
- `split_have_need()` 함수 개선 (정규화 로직 추가)

#### `back/.env` 및 `back/.env.example`
```bash
LLM_PROVIDER=anthropic  # 또는 "mock"
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000
```

## 사용 방법

### 1. 패키지 설치

```bash
cd back
pip install -r requirements.txt
```

### 2. API 키 설정

#### 방법 A: 환경 변수로 설정
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

#### 방법 B: .env 파일 수정
```bash
# back/.env
ANTHROPIC_API_KEY=sk-ant-api03-...
LLM_PROVIDER=anthropic
```

### 3. Mock 모드로 테스트 (API 키 불필요)

API 키 없이 더미 데이터로 테스트:

```bash
# .env 파일 수정
LLM_PROVIDER=mock

# 또는 환경 변수로
LLM_PROVIDER=mock python test_llm_integration.py
```

### 4. 실제 API로 테스트

```bash
cd back
python test_llm_integration.py
```

예상 출력:
```
============================================================
✅ 레시피 생성 성공! (ID: rec_abc123)
============================================================

[레시피 1] 김치 계란볶음밥
  조리 시간: 12분
  인분: 1인분
  요약: 냉장고 속 재료로 5분만에 완성하는 간편 한끼
  ...
```

### 5. 서버 실행

```bash
cd back
uvicorn app.main:app --reload --port 8000
```

## API 사용 예시

### 요청
```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "ingredients": ["계란", "김치", "양파"],
    "constraints": {
      "time_limit_min": 15,
      "servings": 1,
      "tools": ["프라이팬"],
      "exclude": ["우유"]
    }
  }'
```

### 응답
```json
{
  "id": "rec_abc123",
  "created_at": "2026-02-01T01:23:45Z",
  "recipes": [
    {
      "title": "김치 계란볶음밥",
      "time_min": 12,
      "servings": 1,
      "summary": "냉장고 속 재료로 빠르게 만드는 한끼",
      "ingredients_total": ["밥", "김치", "계란", "참기름"],
      "ingredients_have": ["김치", "계란"],
      "ingredients_need": ["밥", "참기름"],
      "steps": ["...", "...", "..."],
      "tips": ["김치는 잘게 썰어 볶으면 더 맛있어요"],
      "warnings": []
    }
    // ... 총 3개 레시피
  ],
  "shopping_list": [
    {"item": "밥"},
    {"item": "참기름"}
  ]
}
```

## 핵심 기능

### 1. LLM 어댑터 (`RecipeLLMAdapter`)

**주요 기능:**
- Claude API 호출하여 3개 레시피 생성
- 사용자 재료, 시간 제한, 제외 재료 등 제약사항 반영
- JSON 응답 파싱 및 Pydantic 모델 변환
- 재시도 로직 (최대 2회)
- 실패 시 더미 데이터 폴백

**시스템 프롬프트 핵심:**
```
- 정확히 3개의 레시피 생성
- 각 레시피는 4-8개 조리 단계
- 모든 텍스트 한국어
- 사용자 시간 제한 준수
- 제외 재료 절대 사용 금지
```

### 2. Mock 어댑터 (`MockRecipeLLMAdapter`)

**사용 시나리오:**
- API 키 없이 개발/테스트
- CI/CD 파이프라인
- 로컬 개발 환경

**설정:**
```bash
LLM_PROVIDER=mock
```

### 3. 검증 시스템

`validation.py`의 엄격한 규칙 유지:
- ✅ 정확히 3개 레시피
- ✅ 각 레시피 4-8개 스텝
- ✅ time_min ≤ time_limit_min
- ✅ 제외 재료 강제 (제목/재료/단계 모두 체크)

### 4. 재료 매칭 로직

`split_have_need()` 함수:
- 대소문자 구분 없이 비교
- 공백 정규화
- 원본 케이스 유지

```python
user_ingredients = ["계란", "김치"]
recipe_ingredients = ["계란", "밥", "간장"]
→ have: ["계란"], need: ["밥", "간장"]
```

## 비용 및 성능

### 예상 비용 (Claude Sonnet 4.5)
- 입력: ~500 토큰 @ $3/M = $0.0015
- 출력: ~1500 토큰 @ $15/M = $0.0225
- **총: 약 $0.024/요청 (약 30원)**

### 응답 시간
- 평균: 3-5초
- 재시도 포함: 최대 10-15초

### 최적화 방안
1. 프롬프트 캐싱 (Anthropic Prompt Caching)
2. 동일 재료 조합 결과 캐싱 (Redis)
3. 배치 요청 처리

## 에러 핸들링

### 1. API 키 미설정
```
ValueError: ANTHROPIC_API_KEY가 설정되지 않았습니다
```
→ `.env` 파일에 API 키 추가 또는 Mock 모드 사용

### 2. API 호출 실패
- 재시도 2회
- 최종 실패 시 더미 레시피 반환 (사용자에게는 정상 응답)

### 3. JSON 파싱 실패
```
ValueError: JSON 파싱 실패
```
→ 재시도 또는 더미 레시피 폴백

### 4. 검증 실패
```
ValueError: recipes_must_be_3
ValueError: time_limit_exceeded
ValueError: exclude_ingredient_detected
```
→ LLM이 규칙 위반 시 에러 발생 (정상 동작)

## 프롬프트 개선 가이드

### 현재 프롬프트 위치
`back/app/services/llm_adapter.py:_build_system_prompt()`

### 개선 방향
1. **Few-shot Examples 추가**: 더 일관된 출력
2. **분량 단위 명시**: "큰술", "작은술", "g", "ml"
3. **재료명 표준화**: "파" vs "대파" vs "쪽파"
4. **이미지 설명 추가**: 비주얼 레시피 생성 준비

### 테스트 방법
1. `llm_adapter.py` 수정
2. `python test_llm_integration.py` 실행
3. 출력 품질 확인
4. 필요 시 temperature 조정 (현재 0.7)

## 프론트엔드 연동

**변경사항 없음!** 백엔드 API 응답 형식이 동일하므로 프론트엔드는 그대로 사용 가능.

```typescript
// front/lib/api.ts (변경 불필요)
const response = await createRecommendation({
  ingredients: ["계란", "김치"],
  constraints: { time_limit_min: 15, servings: 1 }
});
// → 더미 데이터 대신 LLM 생성 레시피 반환
```

## 다음 단계

### 우선순위 높음
1. **API 키 발급 및 설정**
   - Anthropic Console에서 발급
   - .env 파일에 추가

2. **실제 API 테스트**
   - 다양한 재료 조합 테스트
   - 제외 재료 테스트
   - 시간 제한 테스트

3. **프롬프트 품질 개선**
   - 실제 출력 확인 후 프롬프트 튜닝

### 우선순위 중간
4. **캐싱 구현**
   - 동일 재료 조합 결과 캐싱 (Redis 또는 인메모리)
   - 비용 절감 + 응답 속도 개선

5. **모니터링 추가**
   - LLM 호출 성공/실패율
   - 평균 응답 시간
   - 검증 실패 사례 로깅

### 우선순위 낮음
6. **영어 레시피 지원**
   - `language: "en"` 파라미터 활용
   - 프롬프트 다국어화

7. **이미지 생성**
   - SVG 또는 AI 이미지 생성 통합

## 문제 해결

### Q: "ANTHROPIC_API_KEY가 설정되지 않았습니다" 에러
**A:** .env 파일 확인 또는 Mock 모드 사용
```bash
LLM_PROVIDER=mock uvicorn app.main:app --reload
```

### Q: 레시피가 항상 같게 나와요
**A:** Mock 모드 사용 중입니다. 실제 API 사용:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Q: 응답이 느려요 (10초 이상)
**A:** LLM API 호출 시간입니다. 캐싱 구현으로 개선 가능.

### Q: 가끔 더미 레시피가 나와요
**A:** LLM API 실패 시 폴백입니다. 로그 확인:
```bash
tail -f logs/app.log | grep "LLM 생성 실패"
```

## 참고 자료

- [Anthropic API 문서](https://docs.anthropic.com/)
- [Claude Sonnet 4.5 모델 정보](https://www.anthropic.com/claude)
- [Pydantic 검증](https://docs.pydantic.dev/)
- [FastAPI 비동기 처리](https://fastapi.tiangolo.com/async/)

## 라이센스

MIT License (프로젝트 루트의 LICENSE 파일 참고)
