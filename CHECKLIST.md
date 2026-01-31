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
- [x] `/api/v1/recommendations` POST 구현 (현재 더미 생성)
- [x] `/api/v1/recommendations/{id}` GET 구현 (현재 인메모리 조회)
- [ ] LLM 호출 모듈 분리(서비스 레이어)  
  - 현재 서비스는 있으나( `recommendation_service.py`) LLM 어댑터 모듈은 미구현
- [ ] 검증 실패 시 재시도(최대 N회) (LLM 연동 시 적용)
- [ ] DB 저장(요청/응답, 타임스탬프, 옵션)

## 3. 프론트(Next.js)
- [x] 입력 페이지 `/` (재료+옵션)
- [x] 결과 페이지 `/r/[id]` 렌더
- [~] 로딩/에러 UI (기본 처리만 있음 → 디자인/메시지 개선 여지)
- [ ] 공유 링크 UI(복사 버튼)

## 4. 쿠팡 파트너스
- [ ] shoppingList 아이템 → 쿠팡 검색 링크 변환
- [ ] 파트너스 딥링크 적용(가능 범위 확인)

## 5. 품질/테스트
- [ ] 테스트 케이스 30개 만들기(재료 조합/제외재료)
- [ ] 생성 성공률/응답시간 측정
- [ ] 이상한 레시피(30분/오븐 등) 차단 룰 보강

## 6. 배포
- [ ] Render에 FastAPI 배포
- [ ] Vercel에 Next.js 배포
- [ ] CORS/ENV 점검
- [ ] 로그/모니터링 확인
