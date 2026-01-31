# STATUS — 현재까지 진행 상황 (2026-01-31)

## ✅ 현재 동작 확인
- Backend(FastAPI): 실행 및 `/health` 응답 확인 (예: `http://localhost:8100/health` → `{ "ok": true, "env": "dev" }`)
- API:
  - `POST /api/v1/recommendations` 동작 (현재는 **더미 응답 + 인메모리 저장**)
  - `GET /api/v1/recommendations/{id}` 동작 (서버 재시작 시 데이터 소실)
- Front(Next.js): 입력 → 결과 페이지(`/r/{id}`)까지 E2E 확인

## 📁 현재 코드 구성(요약)
- `back/app/main.py`: FastAPI 앱, CORS, `/health`, `/api/v1` 라우팅
- `back/app/api/v1/endpoints/recommendations.py`: POST/GET 엔드포인트
- `back/app/models/recommendation.py`: Pydantic 스키마
- `back/app/services/recommendation_service.py`: 더미 생성 + `_STORE` 인메모리 저장
- `back/app/services/validation.py`: 최소 검증(레시피 3개, 시간 제한, exclude 포함 여부, steps 길이)
- `front/app/page.tsx`: 입력 폼
- `front/app/r/[id]/page.tsx`: 결과 렌더
- `front/lib/api.ts`: API 호출

## ⚠️ 현재 한계/리스크
- 추천 결과가 더미(LLM 미연동)
- 레시피 사진은 임시 `image_url`(Unsplash) 기반(정식 이미지 전략은 추후)
- DB 미연동: 공유 링크/히스토리 지속성 없음(재시작 시 소실)
- 쿠팡 파트너스 링크 미연동
- 프론트 UX: 공유 링크 복사 버튼/장보기 링크 버튼 등 미구현
- 환경:
  - Windows에서는 Python/py launcher/pyenv 구성 이슈가 있었음
  - Mac에서는 정상 실행 확인(단, 명령어는 Mac 방식으로)

## 🎯 다음 작업 후보(우선순위)
1) 보완 포인트 반영(포리님이 말한 개선사항) → 스펙 확정
2) LLM 연동(스키마 고정 JSON + 검증/재시도)
3) DB(Postgres) 저장으로 전환
4) 쿠팡 파트너스 링크 생성
