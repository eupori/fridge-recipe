# 이미지 검색 빠른 시작 가이드

**5분 안에 시작하기** - Mock 모드로 즉시 개발 가능!

---

## 🚀 가장 빠른 방법 (API 키 불필요)

### 1. Mock 모드 사용

```bash
cd back
source .venv/bin/activate

# .env 파일 수정
echo "IMAGE_SEARCH_PROVIDER=mock" >> .env

# 테스트
IMAGE_SEARCH_PROVIDER=mock python test_image_search.py
```

**결과:** 플레이스홀더 이미지 자동 생성 ✅

### 2. 백엔드 실행

```bash
uvicorn app.main:app --reload --port 8000
```

### 3. 프론트엔드 실행

새 터미널:
```bash
cd front
npm run dev
```

**완료!** http://localhost:3000 에서 레시피 생성 시 이미지 표시됨

---

## 📈 단계별 업그레이드

### 레벨 1: Mock (개발용) - 0분 설정

```bash
IMAGE_SEARCH_PROVIDER=mock
```

- ✅ API 키 불필요
- ✅ 즉시 사용 가능
- ✅ 플레이스홀더 이미지

### 레벨 2: Unsplash (기본) - 0분 설정

```bash
IMAGE_SEARCH_PROVIDER=unsplash
```

- ✅ API 키 불필요
- ✅ 실제 이미지
- ⚠️ 정확도 낮음 (30-50%)

### 레벨 3: Google (권장) - 10분 설정

```bash
IMAGE_SEARCH_PROVIDER=google
GOOGLE_API_KEY=your-key
GOOGLE_SEARCH_ENGINE_ID=your-id
```

- ✅ 높은 정확도 (80-90%)
- ✅ 한국 음식 최적화
- ⚠️ API 키 필요 (무료 100/day)

**설정 가이드:** `GOOGLE_API_SETUP_CHECKLIST.md` 참고

---

## 🔧 환경 변수 한눈에 보기

### back/.env

```bash
# Mock (즉시 시작)
IMAGE_SEARCH_PROVIDER=mock

# Unsplash (기본)
IMAGE_SEARCH_PROVIDER=unsplash

# Google (최고 품질)
IMAGE_SEARCH_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
GOOGLE_SEARCH_ENGINE_ID=a1b2c3...
IMAGE_SEARCH_TIMEOUT=3
IMAGE_CACHE_ENABLED=true
```

---

## ✅ 테스트

```bash
cd back

# 이미지 검색만 테스트
IMAGE_SEARCH_PROVIDER=mock python test_image_search.py

# 전체 통합 테스트
LLM_PROVIDER=mock IMAGE_SEARCH_PROVIDER=mock python test_llm_integration.py
```

---

## 📚 더 알아보기

- **상세 문서:** `IMAGE_SEARCH_README.md`
- **Google API 설정:** `GOOGLE_API_SETUP_CHECKLIST.md`
- **전체 가이드:** `CLAUDE.md`

---

**추천 설정:**

| 환경 | LLM | Image Search |
|------|-----|--------------|
| 개발 | mock | mock |
| 테스트 | mock | unsplash |
| 프로덕션 | anthropic | google |
