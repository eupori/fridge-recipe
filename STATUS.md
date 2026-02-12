# STATUS — 현재까지 진행 상황 (2026-02-12)

## ✅ 현재 동작 확인
- Backend(FastAPI): 실행 및 `/health` 응답 확인
- **LLM 연동 완료**: Claude Sonnet 4.5로 실제 레시피 생성
- **이미지 검색/생성 완료**: Google Custom Search + Gemini Imagen
- API:
  - `POST /api/v1/recommendations` 동작 (LLM 연동 + 인메모리 저장)
  - `GET /api/v1/recommendations/{id}` 동작 (서버 재시작 시 데이터 소실)
  - `POST /api/v1/auth/signup`, `POST /api/v1/auth/login` 동작
  - `GET/POST /api/v1/favorites` 동작
- Front(Next.js): 입력 → 결과 페이지(`/r/{id}`)까지 E2E 확인
- **사용자 인증**: JWT 기반 로그인/회원가입
- **즐겨찾기**: 레시피 저장 기능

## 📁 현재 코드 구성(요약)
- `back/app/main.py`: FastAPI 앱, CORS, `/health`, `/api/v1` 라우팅
- `back/app/routers/recommendations.py`: POST/GET 엔드포인트
- `back/app/models/recommendation.py`: Pydantic 스키마
- `back/app/services/recommendation_service.py`: LLM 호출 + `_STORE` 인메모리 저장
- `back/app/services/llm_adapter.py`: Claude API 통합 및 프롬프트 관리
- `back/app/services/image_search_service.py`: 이미지 검색/생성 (Google/Gemini/Unsplash/Mock)
- `back/app/services/validation.py`: 검증 (레시피 3개, 시간 제한, 알러지 파생 재료 등)
- `front/app/page.tsx`: 입력 폼 (usePersistedState로 데이터 유지, Pantry 연동)
- `front/app/r/[id]/page.tsx`: 결과 렌더 + 즐겨찾기
- `front/app/pantry/page.tsx`: 보유 재료 관리 (localStorage 기반)
- `front/app/login/page.tsx`, `front/app/signup/page.tsx`: 인증 페이지
- `front/components/Navbar.tsx`: 공통 네비게이션 바
- `front/lib/api.ts`: API 호출
- `front/hooks/usePersistedState.ts`: localStorage 기반 상태 유지

## ✅ 최근 완료된 이슈 (2026-02-12)
1. **풀스크린 로딩 오버레이** - 진행 단계 표시 + 요리 팁 애니메이션
2. **Google 애드센스 설정** - ads.txt, 메타태그, 스크립트 삽입
3. **도메인 설정** - `eupori.dev` + `recipe.eupori.dev` 모두 Vercel 연결
4. **robots.txt 추가** - 크롤러 접근 허용
5. **.gitignore 정리** - 빌드 캐시, 설정 파일 제외

## ✅ 이전 완료 이슈 (2026-02-09)
1. 새로고침 후 재료값 유지 (`usePersistedState` 훅)
2. 로딩 UI 개선 (스피너, 폼 비활성화, 상태 메시지)
3. 로그인 후 원래 페이지로 리다이렉트 (`returnUrl` 처리)
4. 인원수 4인까지 확장
5. 알러지 파생 재료 검증 (토마토→케첩 등 25개 매핑)
6. **공통 Navbar 컴포넌트** - 로고, 보유재료, 즐겨찾기, 로그인/로그아웃
7. **Pantry (보유 재료 관리)** - `/pantry` 페이지, localStorage 기반

## ⚠️ 현재 한계/리스크
- DB 미연동: 공유 링크/히스토리 지속성 없음(재시작 시 소실)
- 쿠팡 파트너스 링크 미연동
- 프론트 UX: 공유 링크 복사 버튼 미구현

## 🎯 다음 작업 후보 (우선순위)

### 쉬움 (프론트엔드만)
1. **공유 링크 복사 버튼** - 레시피 결과 페이지에 추가

### 어려움 (DB 마이그레이션 필요)
2. **이슈 8: 레시피 좋아요 시스템** - 다른 사용자의 좋아요 집계
3. **이슈 9: 최근 검색 기록 7일 보관**
4. DB(PostgreSQL) 저장으로 전환
5. 쿠팡 파트너스 링크 생성
