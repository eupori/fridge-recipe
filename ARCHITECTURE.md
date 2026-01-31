# ARCHITECTURE

## High-level
- Client(Next.js) → FastAPI
- FastAPI → (LLM API) + DB(Postgres) + Coupang 링크 생성

## Deploy
- Front: Vercel
- Back: Render (Web Service)
- DB: Supabase/Neon 등 외부 Postgres 권장

## Notes
- MVP는 인증 없이도 가능: `result_id` 기반 공유/조회
- 추후 로그인 도입 시: user_id 연결 + 즐겨찾기/히스토리 제공
