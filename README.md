# 냉탐정 - 냉장고 파먹기 레시피

> 냉장고 재료를 입력하면 15분 이내 레시피 3개 + 통합 장보기 리스트를 추천해주는 웹 서비스

**Live:** [eupori.dev](https://eupori.dev)

## 주요 기능

- **AI 레시피 추천** — Claude Sonnet 4.5 기반, 사용자 재료/시간/도구 고려
- **AI 이미지 생성** — Gemini로 레시피별 고품질 음식 이미지 생성
- **YouTube 참고 영상** — 정밀 모드에서 관련 인기 요리 영상 자동 연결
- **통합 장보기 리스트** — 부족 재료를 쿠팡/네이버쇼핑 원클릭 검색
- **보유 재료 관리** — 냉장고 재료 등록 후 레시피 검색 시 자동 불러오기
- **레시피 품질 선택** — 빠른/표준/정밀 3단계 (정밀: 영양 정보, 대체 재료, 보관 팁, 참고 영상)
- **카카오톡 공유** — Feed 템플릿 기반 레시피 공유
- **다크 모드** — FOUC 방지 + localStorage 기반

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Pydantic, SQLAlchemy |
| **Database** | PostgreSQL (Supabase) |
| **AI** | Claude Sonnet 4.5 (레시피), Gemini 2.0 Flash (이미지) |
| **Infra** | Vercel (프론트), EC2 + Docker Compose (백엔드), Nginx, Let's Encrypt |
| **CI/CD** | GitHub Actions (자동배포) |
| **Monitoring** | Sentry (프론트+백엔드) |

## 아키텍처

```
사용자 → Vercel (Next.js SSR) → EC2 (Nginx → FastAPI)
                                        ↓
                              Claude API (레시피 생성)
                              Gemini API (이미지 생성)
                              YouTube API (참고 영상)
                              Supabase (PostgreSQL)
```

## 로컬 개발

```bash
# 백엔드
cd back
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # API 키 설정
uvicorn app.main:app --reload --port 8000

# 프론트엔드
cd front
npm install
cp .env.local.example .env.local
npm run dev
```

Mock 모드 (API 키 없이):
```bash
LLM_PROVIDER=mock IMAGE_SEARCH_PROVIDER=mock uvicorn app.main:app --reload
```

## 프로젝트 구조

```
fridge-recipe/
├── front/                 # Next.js 14 (App Router)
│   ├── app/               # 페이지 라우팅
│   ├── components/        # 재사용 컴포넌트
│   └── lib/               # API 클라이언트, 유틸리티
├── back/                  # FastAPI
│   └── app/
│       ├── api/           # 엔드포인트
│       ├── core/          # 설정, DB
│       ├── models/        # SQLAlchemy + Pydantic 모델
│       └── services/      # 비즈니스 로직
└── docs/                  # 프로젝트 문서
```
