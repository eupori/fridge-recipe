# CHECKLIST — 실행 체크리스트

> 진행하면서 [ ] → [x] 로 업데이트

## 0. 킥오프
- [x] 리포지토리/폴더 구조 확정 (front/back 분리)
- [x] 기본 스캐폴딩 생성(Next.js 기본 페이지 + FastAPI 라우터/모델 뼈대)
- [x] pyenv 지원 파일 추가(back: `.python-version`, `runtime.txt`)
- [~] 환경변수 목록 정리(LLM 키, DB URL, COUPANG 키 등)  
  - back `.env.example` / front `.env.local.example`은 있음 (실제 값 채우기는 진행 중)

## 1. API/스키마
- [~] Recommendation 요청/응답 JSON 스키마 확정  
  - `API_SPEC.md` 초안 완료
  - `image_url` 필드 추가(레시피 사진 표시)
  - `ingredients_total` 필드 추가(레시피 총 재료 표시)
- [x] Pydantic 모델 작성 (`back/app/models/recommendation.py`) + `image_url` 반영
- [x] 검증 규칙(시간/금지재료/steps 길이) 정의 (`back/app/services/validation.py`)
- [ ] 보유/추가 재료 누락 방지 규칙 강화(LLM 연동 시 최우선)

## 2. 백엔드(FastAPI)
- [x] 프로젝트 생성/라우팅
- [x] `/api/v1/recommendations` POST 구현 (LLM 연동 완료)
- [x] `/api/v1/recommendations/{id}` GET 구현 (현재 인메모리 조회)
- [x] LLM 호출 모듈 분리(서비스 레이어) - `llm_adapter.py` 구현 완료
- [x] 검증 실패 시 재시도(최대 N회) - LLM 어댑터에 구현됨
- [x] 알러지 파생 재료 검증 강화 (`validation.py`에 DERIVATIVE_INGREDIENTS 추가)
- [ ] DB 저장(요청/응답, 타임스탬프, 옵션)

## 3. 프론트(Next.js)
- [x] 입력 페이지 `/` (재료+옵션)
- [x] 결과 페이지 `/r/[id]` 렌더
- [x] 로딩/에러 UI (스피너, 폼 비활성화, 상태 메시지)
- [x] 새로고침 후 폼 데이터 유지 (`usePersistedState` 훅)
- [x] 로그인 후 원래 페이지로 리다이렉트 (`returnUrl` 처리)
- [x] 인원수 선택 (1-4인)
- [ ] 공유 링크 UI(복사 버튼)
- [x] 공통 Navbar 컴포넌트 (로고, 보유재료, 즐겨찾기, 로그인)
- [x] Pantry 페이지 (`/pantry`) - 보유 재료 관리

## 4. 쿠팡 파트너스
- [ ] shoppingList 아이템 → 쿠팡 검색 링크 변환
- [ ] 파트너스 딥링크 적용(가능 범위 확인)

## 5. 품질/테스트
- [ ] 테스트 케이스 30개 만들기(재료 조합/제외재료)
- [ ] 생성 성공률/응답시간 측정
- [ ] 이상한 레시피(30분/오븐 등) 차단 룰 보강

## 6. 배포
- [x] ~~AWS Lambda에 FastAPI 배포 (SAM + Docker)~~ → EC2로 마이그레이션 완료
- [x] EC2 (t3.small) + Docker Compose (Nginx + FastAPI) 배포
- [x] Vercel에 Next.js 배포
- [x] 도메인 설정 (`eupori.dev`, `recipe.eupori.dev`, `recipe-api.eupori.dev`)
- [x] GitHub Actions 자동배포 (백엔드, SSH → EC2 docker compose)
- [x] Let's Encrypt SSL 인증서 + 자동 갱신
- [x] CORS/ENV 점검
- [ ] 로그/모니터링 확인 (Sentry 등)
- [ ] Lambda 리소스 정리 (CloudFormation 스택, ECR 이미지)

## 7. 기능 이슈 트래킹
### ✅ 완료 (5건)
- [x] 이슈 1: 새로고침 후 재료값 유지 (`usePersistedState` 훅)
- [x] 이슈 2: 로딩 UI 개선 (스피너, 폼 비활성화)
- [x] 이슈 3: 로그인 후 `returnUrl` 처리
- [x] 이슈 4: 인원수 4인까지 확장
- [x] 이슈 5: 알러지 파생 재료 검증 (토마토→케첩 등)

### ✅ 완료 (7건) - 2026-02-09 추가
- [x] 이슈 6: 공통 Navbar 컴포넌트
- [x] 이슈 7: Pantry - 보유 재료 관리 (localStorage 기반)

### ✅ 완료 (4건) - 2026-02-10 추가
- [x] 이슈 8: 레시피 좋아요(즐겨찾기) 시스템 (SQLite DB)
- [x] 이슈 9: 최근 검색 기록 7일 보관 (SQLite DB)
- [x] 이슈 10: 장보기 목록에서 보유재료로 바로 추가 기능
- [x] 이슈 11: 즐겨찾기 중복 등록 버그 수정 + not_found 에러 안내 개선

### ✅ 완료 (3건) - 2026-02-12 추가
- [x] 이슈 12: 풀스크린 로딩 오버레이 (진행 단계 + 요리 팁)
- [x] 이슈 13: Google 애드센스 설정 (ads.txt, 스크립트, 도메인)
- [x] 이슈 14: 도메인 설정 정리 (`eupori.dev` + `recipe.eupori.dev`)

### ✅ 완료 (1건) - 2026-02-14 추가
- [x] 이슈 15: EC2 마이그레이션 (Lambda → EC2 Docker Compose, Nginx + SSL)

### 📋 남은 이슈
- [ ] 이슈 16: PostgreSQL 마이그레이션
- [ ] 이슈 17: 추천 데이터 DB 저장 (서버 재시작 시 데이터 유지)
- [ ] 이슈 18: 프론트엔드 자동배포 (Vercel GitHub 연동 또는 GitHub Actions)
- [ ] 이슈 19: `eupori.dev` 랜딩페이지 개발 시 도메인 분리
- [ ] 이슈 20: Lambda 리소스 정리 (CloudFormation 스택 삭제, ECR 이미지 삭제, template.yaml 삭제)
