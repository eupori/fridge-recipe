# Google Custom Search API 설정 체크리스트

Google API를 사용하여 레시피 이미지 검색 정확도를 80-90%로 향상시키려면 다음 단계를 따르세요.

---

## ✅ 단계별 체크리스트

### 1. Google Cloud Console 설정

- [ ] https://console.cloud.google.com 접속
- [ ] 프로젝트 생성 또는 기존 프로젝트 선택
  - 프로젝트명 예: "fridge-recipe-prod"
- [ ] **Custom Search API** 활성화
  1. 왼쪽 메뉴: APIs & Services → Library
  2. 검색: "Custom Search API"
  3. "ENABLE" 클릭
- [ ] API 키 생성
  1. APIs & Services → Credentials
  2. "+ CREATE CREDENTIALS" → "API key"
  3. 생성된 키 복사 (예: `AIzaSyBkR...`)
  4. (선택) "Restrict Key" 클릭하여 보안 설정
     - Application restrictions: None 또는 IP addresses
     - API restrictions: Custom Search API만 선택

**복사한 API 키:**
```
GOOGLE_API_KEY=AIzaSy________________________
```

---

### 2. Programmable Search Engine 생성

- [ ] https://programmablesearchengine.google.com 접속
- [ ] "새 검색 엔진 추가" 또는 "Add" 클릭
- [ ] 검색 엔진 설정:
  - **이름:** Fridge Recipe Image Search
  - **검색할 사이트:** "전체 웹 검색" 선택 (Search the entire web)
  - **언어:** Korean (또는 English)
  - **지역:** Korea (선택사항)
- [ ] "만들기" 또는 "Create" 클릭
- [ ] 생성된 검색 엔진 설정으로 이동
- [ ] **중요:** "이미지 검색" ON (Image search: ON)
  - "Setup" → "Basic" → Image search: **ON**
- [ ] "세이프서치" ON (SafeSearch: ON) - 권장
- [ ] Search Engine ID 복사
  - 형식: `a1b2c3d4e5f6g7h8i` (약 17자)

**복사한 Search Engine ID:**
```
GOOGLE_SEARCH_ENGINE_ID=________________________
```

---

### 3. 환경 변수 설정

- [ ] `back/.env` 파일 열기
- [ ] 다음 변수 추가/수정:

```bash
# Image Search
IMAGE_SEARCH_PROVIDER=google
GOOGLE_API_KEY=AIzaSy________________________  # 1단계에서 복사한 키
GOOGLE_SEARCH_ENGINE_ID=a1b2c3d4e5_________   # 2단계에서 복사한 ID
IMAGE_SEARCH_TIMEOUT=3
IMAGE_CACHE_ENABLED=true
```

- [ ] 파일 저장

---

### 4. 테스트

#### 4-1. 이미지 검색 단독 테스트

```bash
cd back
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Google API 테스트
IMAGE_SEARCH_PROVIDER=google python test_image_search.py
```

**예상 결과:**
```
✅ 성공: https://encrypted-tbn0.gstatic.com/images?q=...
✅ 성공: https://...
```

**문제 발생 시:**
```
❌ Google API HTTP 에러 403: ...
→ API 키 또는 Search Engine ID 확인
```

#### 4-2. 통합 테스트

```bash
# LLM + 이미지 검색 통합 테스트
LLM_PROVIDER=anthropic IMAGE_SEARCH_PROVIDER=google python test_llm_integration.py
```

**예상 결과:**
```
✅ 레시피 생성 성공!
[레시피 1] 김치볶음밥
  이미지: https://...
```

#### 4-3. 백엔드 서버 테스트

```bash
# 백엔드 실행
uvicorn app.main:app --reload --port 8000
```

새 터미널에서:
```bash
cd front
npm run dev
```

브라우저에서 http://localhost:3000 접속하여 레시피 생성 후 이미지 확인

---

### 5. API 사용량 모니터링

- [ ] Google Cloud Console → APIs & Services → Dashboard
- [ ] "Custom Search API" 클릭
- [ ] "Quotas" 탭 확인
  - Queries per day: 0 / 100 (무료)
  - 매일 사용량 확인

**할당량 초과 시:**
- Unsplash로 자동 폴백됨 (정상 동작)
- 또는 유료 플랜 활성화 ($5/1000 queries)

---

## 🐛 문제 해결

### 문제 1: "API 키가 유효하지 않습니다" (403 Forbidden)

**원인:**
- API 키가 잘못됨
- Custom Search API가 활성화되지 않음

**해결:**
1. Google Cloud Console → APIs & Services → Credentials
2. API 키 재확인 (복사/붙여넣기 오류 확인)
3. APIs & Services → Library → Custom Search API → "ENABLE" 확인

---

### 문제 2: "Search Engine ID가 유효하지 않습니다" (400 Bad Request)

**원인:**
- Search Engine ID가 잘못됨
- 검색 엔진이 삭제됨

**해결:**
1. https://programmablesearchengine.google.com
2. 생성한 검색 엔진 확인
3. Search Engine ID 재복사

---

### 문제 3: "이미지 검색 결과 없음"

**원인:**
- 이미지 검색이 비활성화됨

**해결:**
1. Programmable Search Engine 설정
2. Setup → Basic → Image search: **ON** 확인
3. 변경 사항 저장

---

### 문제 4: "할당량 초과" (429 Too Many Requests)

**원인:**
- 일일 100 queries 초과

**해결:**
1. 캐싱 확인: `IMAGE_CACHE_ENABLED=true`
2. Unsplash로 자동 폴백됨 (정상 동작)
3. 내일 다시 사용 가능
4. 또는 유료 플랜 활성화

---

### 문제 5: 테스트는 성공하는데 프론트엔드에서 이미지 안 나옴

**원인:**
- CORS 이슈
- 이미지 URL이 깨짐

**해결:**
1. 백엔드 로그 확인: `이미지 검색 성공` 메시지 확인
2. 프론트엔드 개발자 도구 → Network 탭
3. 이미지 URL 상태 확인

---

## 💡 팁

### 개발 중에는 Mock 모드 사용

API 할당량을 절약하려면:

```bash
# .env
IMAGE_SEARCH_PROVIDER=mock  # 플레이스홀더 이미지
```

### 프로덕션 배포 시

```bash
# .env (프로덕션)
IMAGE_SEARCH_PROVIDER=google
GOOGLE_API_KEY=실제_키
GOOGLE_SEARCH_ENGINE_ID=실제_ID
IMAGE_CACHE_ENABLED=true  # 반드시 켜기
```

### 비용 절감

1. **캐싱 활성화**: `IMAGE_CACHE_ENABLED=true`
2. **인기 레시피 수동 매핑**: 상위 20개는 직접 이미지 URL 지정
3. **모니터링**: 일일 사용량 확인

---

## 📊 예상 사용량

```
일일 레시피 생성: 10회
× 레시피당 이미지: 3개
= 총 30 queries/day

캐시 히트율: 50%
= 실제 API 호출: 15 queries/day

무료 할당량: 100 queries/day
→ 충분함 ✅
```

---

## ✅ 완료 확인

설정이 완료되었다면 다음을 확인하세요:

- [ ] `test_image_search.py` 테스트 성공
- [ ] `test_llm_integration.py` 통합 테스트 성공
- [ ] 백엔드 서버 정상 시작
- [ ] 프론트엔드에서 레시피 이미지 표시됨
- [ ] Google Cloud Console에서 API 사용량 확인 가능

---

**문제가 계속되면:**
- `back/IMAGE_SEARCH_README.md` 참고
- GitHub Issues에 문의
- 또는 `IMAGE_SEARCH_PROVIDER=unsplash`로 폴백 사용

**설정 완료 시:**
- Google API로 80-90% 정확도 달성! 🎉
- 한국 음식 이미지 품질 향상
- 사용자 경험 개선
