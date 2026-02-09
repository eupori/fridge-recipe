# CLAUDE.md - Fridge-Recipe 프로젝트 가이드

## 프로젝트 개요

**Fridge-Recipe**는 한국 사용자(자취생/1인가구·신혼)를 타겟으로 하는 이중언어(한국어/영어) 레시피 추천 웹 애플리케이션입니다. 핵심 기능은 사용자가 냉장고에 있는 재료를 입력하면 15분 이내로 만들 수 있는 레시피 3개와 통합 장보기 리스트를 제공합니다.

**현재 상태:**
- ✅ LLM 통합 완료! Claude Sonnet 4.5를 사용하여 실제 레시피를 생성합니다.
- ✅ 이미지 검색 통합 완료! Google Custom Search API로 한국 음식 이미지 정확도 80-90% 달성
- ✅ Gemini 이미지 생성 통합! AI가 고품질 한국 음식 이미지를 직접 생성합니다.
- ✅ Mock 모드 지원으로 API 키 없이도 개발 가능합니다.

**타겟 사용자:** 빠른 요리 솔루션을 찾는 한국의 1인 가구 및 신혼부부

---

## 한국어 사용 가이드

### 주요 원칙

**이 프로젝트는 한국 사용자를 위한 서비스이므로, 작업 시 다음을 준수하세요:**

1. **사용자 대면 텍스트는 항상 한국어**
   - UI 라벨, 버튼 텍스트, 에러 메시지
   - 레시피 제목, 재료명, 조리 단계
   - 사용자 안내 문구

2. **코드/기술 용어는 영어 유지**
   - 변수명, 함수명, 클래스명
   - Git 커밋 메시지
   - 코드 주석 (선택사항)

3. **데이터 필드명은 영어, 값은 한국어**
   ```python
   # 올바른 예시
   recipe = {
       "title": "김치볶음밥",  # 필드명은 영어, 값은 한국어
       "ingredients": ["밥", "김치", "참기름"]
   }
   ```

4. **백엔드 응답의 언어**
   - `language: "ko"` 요청 시 → 모든 텍스트를 한국어로 반환
   - `language: "en"` 요청 시 → 영어로 반환 (향후 지원 예정)

### 주의사항

- **재료명 표준화:** "파" vs "대파" vs "쪽파" 등 일관성 유지 필요
- **요리 용어:** 한국식 표현 사용 ("볶다", "끓이다" 등)
- **분량 단위:** "큰술", "작은술", "컵", "g", "ml" 등 한국식 계량 단위 사용

---

## 빠른 시작 명령어

### 프론트엔드 (Next.js 14)

```bash
cd front
npm install
npm run dev          # http://localhost:3000 에서 개발 서버 시작
npm run build        # 프로덕션 빌드
npm run lint         # 린터 실행
```

**환경 설정:**
```bash
cp front/.env.local.example front/.env.local
# .env.local 파일을 열어 백엔드 API URL 수정
```

### 백엔드 (FastAPI)

**초기 설정:**
```bash
cd back
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**환경 설정:**
```bash
cp back/.env.example back/.env
# .env 파일을 열어 설정값 수정
```

**서버 실행:**
```bash
cd back
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Python 버전:** 3.11.8 (`.python-version` 및 `runtime.txt` 참고)

---

## 아키텍처

### 모노레포 구조

```
fridge-recipe/
├── front/          # Next.js 14 (App Router, TypeScript)
├── back/           # FastAPI (Pydantic, 인메모리 저장)
└── CLAUDE.md       # 이 파일
```

### 기술 스택

**프론트엔드:**
- Next.js 14 (App Router)
- TypeScript
- React hooks (전역 상태 관리 없음)
- 레시피 페이지 서버사이드 렌더링

**백엔드:**
- FastAPI (Python 3.11)
- Pydantic (데이터 검증)
- 인메모리 저장소 (딕셔너리 기반, 임시)
- CORS 활성화 (로컬 개발용)

### 데이터 흐름

```
사용자 입력 폼 (front/app/page.tsx)
    ↓
POST /api/v1/recommendations
    ↓
백엔드: recommendation_service.generate_recommendations()
    ↓
ID와 함께 메모리에 저장: rec_{10자리 hex}
    ↓
{recommendation_id} 반환
    ↓
프론트엔드: /r/{id}로 리다이렉트
    ↓
GET /api/v1/recommendations/{id}
    ↓
레시피 3개 + 장보기 리스트 표시
```

### 현재 저장 시스템

**위치:** `back/app/services/recommendation_service.py`

- 인메모리 딕셔너리: `_STORE = {}`
- ID 형식: `rec_{uuid.uuid4().hex[:10]}`
- **서버 재시작 시 데이터 손실**
- 아직 데이터베이스 미연동 (계획: Supabase/Neon의 PostgreSQL)

---

## 핵심 파일 및 용도

### 백엔드 핵심 파일

| 파일 | 용도 |
|------|------|
| `back/app/main.py` | FastAPI 앱 초기화, CORS 설정, 라우터 등록 |
| `back/app/core/config.py` | Pydantic Settings - 모든 환경 변수 관리 |
| `back/app/models/recommendation.py` | 요청/응답 Pydantic 스키마 |
| `back/app/services/recommendation_service.py` | **레시피 생성 로직** (현재 더미 데이터) |
| `back/app/services/validation.py` | 응답 검증 규칙 |
| `back/app/routers/recommendations.py` | API 엔드포인트 |

### 프론트엔드 핵심 파일

| 파일 | 용도 |
|------|------|
| `front/app/page.tsx` | 홈페이지 - 재료 입력 폼 |
| `front/app/r/[id]/page.tsx` | 레시피 결과 페이지 (동적 라우트) |
| `front/lib/api.ts` | 중앙화된 API 클라이언트 함수 |
| `front/components/` | React 컴포넌트 (폼, 레시피 카드 등) |

---

## 중요 패턴 및 제약사항

### 백엔드 검증 규칙

**위치:** `back/app/services/validation.py`

백엔드는 생성된 추천에 대해 엄격한 검증을 수행합니다:

1. **정확히 3개의 레시피** 반환 필수
2. **시간 제약:** 각 레시피의 `time_min` ≤ 사용자의 `time_limit_min`
3. **제외 재료 강제:** 제외 재료 및 알레르기 재료는 다음에 등장하면 안 됨:
   - 레시피 제목
   - 재료 목록
   - 조리 단계 텍스트
4. **조리 단계 개수:** 레시피당 4-8개 단계

### 레시피 데이터 구조

```python
Recipe:
  - ingredients_total: List[str]  # 레시피에 필요한 모든 재료
  - ingredients_have: List[str]   # 사용자가 가진 재료 중 매칭되는 것
  - ingredients_need: List[str]   # 구매해야 하는 재료
```

**장보기 리스트 로직:**
- 3개 레시피의 모든 `ingredients_need` 집계
- 중복 제거
- `RecommendationResponse.shopping_list`로 반환

### API 클라이언트 패턴

**위치:** `front/lib/api.ts`

중앙화된 fetch 함수:
```typescript
createRecommendation(data) → {recommendation_id}
getRecommendation(id) → 전체 추천 객체
```

모든 API 호출은 이 클라이언트를 통해야 합니다 - 컴포넌트에서 임의로 fetch 호출하지 마세요.

---

## 핵심 비즈니스 로직

### 레시피 생성 (현재: 더미 데이터)

**위치:** `back/app/services/recommendation_service.py:generate_recommendations()`

**현재 구현:**
- 하드코딩된 한국 레시피 반환
- LLM 사용 안 함
- 사용자 선호도에 대한 검증만 수행

**✅ 구현 완료:**
- Claude Sonnet 4.5 API를 사용한 실제 레시피 생성
- 사용자의 재료, 선호도, 제약사항을 프롬프트 컨텍스트로 활용
- LLM 출력을 구조화된 Pydantic 모델로 파싱
- 재시도 로직 및 폴백 처리
- Mock 모드 지원 (API 키 없이 개발 가능)

**상세 문서:** `back/LLM_INTEGRATION_README.md` 참고

### 요청 파라미터

```python
RecommendationCreate:
  - ingredients: List[str]           # 사용자의 냉장고 재료
  - time_limit_min: int             # 최대 조리 시간
  - exclude_ingredients: List[str]   # 사용하지 않을 재료
  - allergens: List[str]            # 알레르기 필터
  - language: str                   # "ko" 또는 "en"
```

---

## 아직 구현되지 않은 기능

### 완료된 기능

- [x] ✅ 실제 레시피 생성을 위한 LLM 통합 (Claude Sonnet 4.5)
- [x] ✅ 레시피 이미지 검색 (Google Custom Search API)
- [x] ✅ AI 이미지 생성 (Gemini Imagen)
- [x] ✅ 사용자 인증/계정 (JWT 기반 경량 인증)
- [x] ✅ 레시피 즐겨찾기
- [x] ✅ Tailwind CSS 설정

### 계획된 기능

- [ ] PostgreSQL 데이터베이스 (Supabase 또는 Neon) - 배포 후 진행 예정
- [ ] 장보기 리스트용 쿠팡 파트너스 제휴 링크
- [ ] 테스트 인프라 (현재 기본 테스트만 존재)
- [ ] 레시피 평가
- [ ] 영양 정보
- [ ] 레시피 결과 캐싱 (비용 절감)

### 배포 계획

- **프론트엔드:** Vercel
- **백엔드:** Render (Web Service)
- **데이터베이스:** 외부 PostgreSQL (향후)

---

## 일반적인 개발 작업

### 새 API 엔드포인트 추가하기

1. `back/app/models/`에 Pydantic 모델 정의
2. `back/app/services/`에 서비스 로직 작성
3. `back/app/routers/`에 라우터 엔드포인트 추가
4. 새 라우터 파일인 경우 `back/app/main.py`에 라우터 등록
5. `front/lib/api.ts`에 클라이언트 함수 추가
6. React 컴포넌트에서 사용

### 레시피 생성 로직 수정하기

**핵심 파일:**
- `back/app/services/recommendation_service.py` - 진입점 및 재료 매칭 로직 (async)
- `back/app/services/llm_adapter.py` - Claude API 통합 및 프롬프트 관리
- `back/app/services/image_search_service.py` - 이미지 검색 통합 (Google/Unsplash/Mock)

**LLM 프롬프트 수정:**
1. `llm_adapter.py`의 `_build_system_prompt()` 함수 수정
2. `_build_user_prompt()` 함수로 사용자 컨텍스트 구성

**이미지 검색/생성 수정:**
1. `image_search_service.py`의 `KOREAN_FOOD_TRANSLATIONS` 사전에 음식 추가
2. `IMAGE_SEARCH_PROVIDER` 환경 변수로 제공자 선택:
   - `google`: Google Custom Search API (검색 기반)
   - `gemini`: Gemini Imagen (AI 생성, 권장)
   - `unsplash`: Unsplash (폴백용)
   - `mock`: 플레이스홀더 (테스트용)
3. Gemini 사용 시: `GEMINI_API_KEY` 설정 필요
4. `python test_llm_integration.py`로 테스트

**Mock 모드 사용:**
```bash
LLM_PROVIDER=mock python test_llm_integration.py
```

### 프론트엔드 페이지 추가하기

- Next.js App Router 규칙 사용: `front/app/[route]/page.tsx`
- API 호출은 `front/lib/api.ts`의 함수 사용
- 상태 관리는 React hooks 사용 (Redux/Zustand 없음)

---

## 문제 해결

### 백엔드가 시작되지 않을 때
- Python 버전 확인: `python --version` (3.11.x여야 함)
- 가상환경이 활성화되어 있는지 확인
- 모든 의존성 확인: `pip install -r requirements.txt`
- 8000 포트가 사용 중인지 확인

### 프론트엔드가 백엔드에 연결되지 않을 때
- 백엔드가 8000 포트에서 실행 중인지 확인
- `front/.env.local`에 올바른 `NEXT_PUBLIC_API_URL`이 있는지 확인
- `back/app/main.py`에 CORS가 설정되어 있는지 확인

### 백엔드 재시작 후 데이터가 사라짐
- 예상된 동작 - 인메모리 저장소 사용 중
- 영구 저장이 필요하면 데이터베이스 구현

---

## 코드 스타일 및 규칙

### 백엔드
- 모든 요청/응답 데이터에 Pydantic 모델 사용
- 서비스 레이어 패턴 (비즈니스 로직을 라우터에서 분리)
- 모든 함수에 타입 힌트
- I/O 작업에 async/await (향후 DB 호출)

### 프론트엔드
- TypeScript strict 모드
- hooks를 사용한 함수형 컴포넌트
- 기본적으로 서버 컴포넌트 (App Router)
- 필요시에만 클라이언트 컴포넌트 (폼, 인터랙션)

---

## 환경 변수

### 프론트엔드 (`front/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 백엔드 (`back/.env`)
```bash
# FastAPI
APP_ENV=dev
APP_NAME=fridge-recipes
CORS_ORIGINS=http://localhost:3000

# LLM (anthropic 또는 mock)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Image Search (google, gemini, unsplash, 또는 mock)
IMAGE_SEARCH_PROVIDER=gemini
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id-here
IMAGE_SEARCH_TIMEOUT=3
IMAGE_CACHE_ENABLED=true

# Gemini Image Generation (IMAGE_SEARCH_PROVIDER=gemini 사용 시)
# ⚠️ Google Cloud Billing 활성화 필요
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_IMAGE_MODEL=gemini-2.0-flash-exp-image-generation

# Coupang (향후)
COUPANG_PARTNERS_TRACKING_ID=
COUPANG_PARTNERS_SUB_ID=
```

**Mock 모드 (API 키 없이 테스트):**
```bash
LLM_PROVIDER=mock
IMAGE_SEARCH_PROVIDER=mock
```

모든 사용 가능한 설정은 `back/app/core/config.py` 참고.

---

## 도움 받기

코드베이스 작업 시:
1. 아키텍처 및 패턴은 이 파일 참고
2. 핵심 로직은 `back/app/services/recommendation_service.py` 읽기
3. 데이터 구조는 `back/app/models/recommendation.py` 검토
4. 비즈니스 규칙은 `validation.py` 참고

특정 구현에 대한 질문은 git 히스토리 확인:
```bash
git log --oneline
git show <commit-hash>
```

최근 커밋:
- `b60b332` - feat_add_recipe_images_and_total_ingredients
- `5961d53` - back mvp
- `367ecd4` - first commit

---

## Claude Code 작업 시 참고사항

**이 프로젝트에서 작업하는 미래의 Claude 인스턴스를 위한 가이드:**

1. **한국어 우선:** 사용자 대면 기능 작업 시 한국어로 텍스트 생성
2. **LLM 통합 완료:** `llm_adapter.py`에서 Claude API로 실제 레시피 생성 중
   - Mock 모드: `LLM_PROVIDER=mock`으로 API 키 없이 테스트 가능
   - 실제 모드: `ANTHROPIC_API_KEY` 환경 변수 필요
   - 상세 문서: `back/LLM_INTEGRATION_README.md`
3. **이미지 검색/생성 통합 완료:** `image_search_service.py`에서 레시피 이미지 제공
   - Mock 모드: `IMAGE_SEARCH_PROVIDER=mock` (플레이스홀더 이미지)
   - Gemini: `IMAGE_SEARCH_PROVIDER=gemini` (AI 생성, 권장, $0.039/이미지)
   - Google: `IMAGE_SEARCH_PROVIDER=google` (검색 기반, API 키 필요)
   - Unsplash: `IMAGE_SEARCH_PROVIDER=unsplash` (폴백용)
4. **검증 필수:** `validation.py`의 엄격한 규칙 준수 (3개 레시피, 4-8 스텝, 시간 제한, 제외 재료)
5. **인메모리 저장:** 데이터 영속성 없음을 인지하고 작업 (서버 재시작 시 데이터 사라짐)
6. **타입 안전성:** Pydantic 모델을 통해 항상 타입 검증
7. **비동기 처리:** 레시피 생성은 async 함수 (`create_recommendation()`), 이미지 검색은 병렬 처리
