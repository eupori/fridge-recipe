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
├── back/           # FastAPI (Pydantic, SQLAlchemy + PostgreSQL)
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
- SQLAlchemy + PostgreSQL (프로덕션) / SQLite (로컬 개발)
- CORS 활성화

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

### 저장 시스템

- SQLAlchemy ORM + PostgreSQL (프로덕션: Supabase)
- 로컬 개발: SQLite 자동 폴백 (`fridge_recipe.db`)
- ID 형식: `rec_{uuid.uuid4().hex[:10]}`
- 테이블 자동 생성: `create_tables()` (앱 시작 시)

---

## 핵심 파일 및 용도

### 백엔드 핵심 파일

| 파일 | 용도 |
|------|------|
| `back/app/main.py` | FastAPI 앱 초기화, CORS 설정, 라우터 등록 |
| `back/app/core/config.py` | Pydantic Settings - 모든 환경 변수 관리 |
| `back/app/models/recommendation.py` | 요청/응답 Pydantic 스키마 |
| `back/app/models/guest_usage.py` | 비로그인 사용자 일일 사용량 추적 모델 |
| `back/app/services/recommendation_service.py` | **레시피 생성 로직** |
| `back/app/services/usage_service.py` | 비로그인 사용량 체크/증가 서비스 |
| `back/app/services/validation.py` | 응답 검증 규칙 |
| `back/app/api/v1/endpoints/recommendations.py` | 추천 API 엔드포인트 (게이팅 포함) |
| `back/app/api/v1/endpoints/stats.py` | 공개 통계 엔드포인트 |

### 프론트엔드 핵심 파일

| 파일 | 용도 |
|------|------|
| `front/app/page.tsx` | 홈페이지 - 재료 입력 폼, 통계, 배너, 게이팅 UI |
| `front/app/r/[id]/page.tsx` | 레시피 결과 페이지 (동적 라우트) |
| `front/lib/api.ts` | 중앙화된 API 클라이언트 함수 |
| `front/components/Navbar.tsx` | 네비게이션 바 + 다크 모드 토글 |
| `front/components/ShareButton.tsx` | 카카오톡/Web Share/클립보드 공유 |
| `front/components/Onboarding.tsx` | 첫 방문 3단계 온보딩 오버레이 |
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

### 레시피 생성

**위치:** `back/app/services/recommendation_service.py`

- Claude Sonnet 4.5 API를 사용한 실제 레시피 생성
- 사용자의 재료, 선호도, 제약사항을 프롬프트 컨텍스트로 활용
- LLM 출력을 구조화된 Pydantic 모델로 파싱
- 재시도 로직 및 폴백 처리
- Mock 모드 지원 (`LLM_PROVIDER=mock`)

**상세 문서:** `back/LLM_INTEGRATION_README.md` 참고

### 요청 파라미터

```python
RecommendationCreate:
  - ingredients: List[str]     # 사용자의 냉장고 재료 (최소 1개)
  - constraints: Constraints   # 조리 제약조건
    - time_limit_min: int      # 최대 조리 시간 (5-60분, 기본 15)
    - servings: int            # 인분 (1-6, 기본 1)
    - tools: List[str]         # 사용 가능한 조리 도구
    - exclude: List[str]       # 제외할 재료
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
- [x] ✅ Sentry 에러 모니터링 (프론트엔드 + 백엔드) + Slack 알림
- [x] ✅ 다크 모드 (FOUC 방지 + Navbar 토글, `localStorage` 기반)
- [x] ✅ 소프트 게이팅 (비로그인 IP 기반 3회/일, 로그인 시 무제한)
- [x] ✅ 사회적 증거 통계 (`/api/v1/stats` → 홈 히어로에 레시피 수/사용자 수 표시)
- [x] ✅ 카카오톡 공유 (Kakao SDK + Feed 템플릿, Web Share API fallback)
- [x] ✅ 온보딩 플로우 (첫 방문 3단계 오버레이, `localStorage` 기반)
- [x] ✅ 로그인 유도 배너 (비로그인 홈페이지 상단, `sessionStorage` 1회 닫기)

### 계획된 기능

- [ ] 장보기 리스트용 쿠팡 파트너스 제휴 링크
- [ ] 테스트 인프라 (현재 기본 테스트만 존재)
- [ ] 레시피 평가
- [ ] 영양 정보
- [ ] Google Analytics 연동

### 배포 구성

- **프론트엔드:** Vercel (`eupori.dev`, `recipe.eupori.dev`)
- **백엔드:** EC2 (t3.small) + Docker Compose (`recipe-api.eupori.dev`)
- **데이터베이스:** PostgreSQL (Supabase)
- **DNS:** Cloudflare (DNS only 모드)
- **자동배포:** GitHub Actions (`back/**` 변경 → EC2), 프론트는 `vercel --prod --yes`

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

### 로컬 개발 시 DB 초기화
- SQLite 사용 시 `fridge_recipe.db` 파일 삭제 후 서버 재시작
- PostgreSQL 사용 시 `DATABASE_URL` 환경 변수 설정

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
NEXT_PUBLIC_KAKAO_JS_KEY=카카오_자바스크립트_키
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

# Guest Usage (비로그인 일일 제한)
GUEST_DAILY_LIMIT=3

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
```bash
git log --oneline -10
```

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
5. **DB 저장:** SQLAlchemy + PostgreSQL (프로덕션), SQLite (로컬)
6. **타입 안전성:** Pydantic 모델을 통해 항상 타입 검증
7. **비동기 처리:** 레시피 생성은 async 함수 (`create_recommendation()`), 이미지 검색은 병렬 처리
8. **다크 모드:** `globals.css`에 `.dark` CSS 변수 정의됨, `tailwind.config.ts`에 `darkMode: ["class"]`, Navbar에 ThemeToggle
9. **소프트 게이팅:** 비로그인 사용자 IP 기반 3회/일 제한 (`guest_usage` 테이블), 로그인 시 무제한
   - `UsageService`가 IP별 일일 사용량 관리
   - 429 응답 시 `RateLimitError` 클래스로 프론트에서 처리
10. **카카오 공유:** `NEXT_PUBLIC_KAKAO_JS_KEY`는 Vercel 환경변수로 설정 (EC2 불필요), SDK 미로드 시 Web Share API fallback
11. **온보딩:** `localStorage("onboarding-done")`으로 첫 방문 감지, 3단계 오버레이
12. **모바일 대응 필수:** UI 작업 시 420px 기준으로 확인. 배너/카드 내 가로 배치 → 모바일에서 세로 배치 또는 줄바꿈 필요
13. **커밋 시 제외 파일:** `back/data/images/`와 `back/data/image_cache.json`은 절대 커밋하지 말 것 (캐시 데이터)
14. **CORS 커스텀 헤더:** 프론트에서 커스텀 응답 헤더(예: `X-Daily-Remaining`) 읽으려면 `expose_headers`에 추가 필수
15. **JSONResponse 주의:** `@router.post(response_model=...)` 데코레이터가 있어도 `JSONResponse`로 직접 반환하면 response_model 검증 우회됨
16. **프론트 환경변수:** `NEXT_PUBLIC_*`는 Vercel 대시보드에서 관리 (EC2와 무관)
