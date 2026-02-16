# 개선 체크리스트 (2026-02-16)

## CRITICAL (즉시 수정)

- [ ] **보안 — JWT 시크릿 하드코딩** `config.py:15` — 기본값 `"change-this-in-production"` 사용 중
- [ ] **보안 — CORS + credentials 위반** `main.py:61-68` — `allow_origins=["*"]` + `allow_credentials=True` 조합
- [ ] **Git — `back/data/` 미제외** — `image_cache.json` + `images/` (~69MB)가 .gitignore에 없음
- [ ] **인프라 — `.env.production` 커밋됨** — 플레이스홀더 키가 Git에 노출

## HIGH (이번 주 수정)

- [ ] **보안 — IP 스푸핑 취약** `recommendations.py:85` — `x-forwarded-for` 헤더 무검증 신뢰
- [ ] **보안 — 인증 사용자 레이트 리밋 없음** — 로그인 시 무제한 요청 가능
- [ ] **DB — UsageService 레이스 컨디션** `usage_service.py:33-53` — 동시 요청 시 이중 카운트
- [ ] **인프라 — Docker 헬스체크 없음** `docker-compose.yml`
- [ ] **인프라 — 배포 후 검증 없음** `deploy-backend.yml`
- [ ] **인프라 — Nginx 보안 헤더 미설정**
- [ ] **프론트 — TypeScript strict 모드 OFF** `tsconfig.json`
- [ ] **테스트 — 자동화 테스트 전무**

## MEDIUM — SEO/마케팅

- [ ] **SEO — JSON-LD 구조화 데이터 없음** `ResultClient.tsx`
- [ ] **SEO — OG 이미지 없음** `layout.tsx`
- [ ] **SEO — Twitter 카드 태그 누락** `r/[id]/page.tsx`
- [ ] **SEO — canonical 링크 없음** `r/[id]/page.tsx`

## MEDIUM — 성능

- [ ] **성능 — React.memo 미적용** `ShareButton.tsx`, `FavoriteButton.tsx`
- [ ] **성능 — 이미지 캐시 크기 제한 없음** `image_search_service.py`
- [ ] **성능 — 통계 API 캐싱 없음** `page.tsx:90-94`
- [ ] **성능 — Nginx gzip 미설정**
- [ ] **성능 — DB 인덱스 누락** `favorite.py`

## MEDIUM — UX

- [ ] **UX — BottomNav "내정보" 라벨 오해** `BottomNav.tsx:11`
- [ ] **UX — 즐겨찾기 빈 화면에 CTA 없음** `favorites/page.tsx:85`
- [ ] **UX — 모바일 터치 타겟 부족** `ShareButton.tsx`
- [ ] **UX — iOS safe-area 미대응** `page.tsx:603-621`
- [ ] **UX — 온보딩 ESC 키 미지원** `Onboarding.tsx`

## MEDIUM — 접근성

- [ ] **접근성 — 재료 색상 구분만 사용** `ResultClient.tsx:352-364`
- [ ] **접근성 — 조리 단계 키보드 조작 불가** `ResultClient.tsx:470`
- [ ] **접근성 — 폼 라벨 미연결** `page.tsx:437-445`

## MEDIUM — 코드 품질

- [ ] **코드 — resolveImageUrl 중복 정의** `r/[id]/page.tsx` + `lib/api.ts`
- [ ] **코드 — API_BASE 재정의** `r/[id]/page.tsx:4-5`
- [ ] **코드 — 에러 메시지 문자열 비교** `page.tsx:475`
- [ ] **코드 — 매직 스트링 산재**
- [ ] **코드 — 에러 메시지 언어 비일관**

## MEDIUM — 인프라

- [ ] **인프라 — 배포 롤백 전략 없음** `deploy-backend.yml`
- [ ] **인프라 — Docker 빌드 캐시 비활성**
- [ ] **인프라 — Docker non-root 실행 안 함** `Dockerfile`
- [ ] **인프라 — 요청 ID 추적 없음**
- [ ] **모니터링 — CloudWatch 알람 없음**

## LOW (여유 시 개선)

- [ ] **UX — 히스토리 로딩 스켈레톤 없음**
- [ ] **UX — 팬트리 삭제 Undo 없음**
- [ ] **UX — 모바일 로고 텍스트 숨김** `Navbar.tsx:45`
- [ ] **성능 — Sentry Session Replay 비활성**
- [ ] **코드 — localStorage 키 상수화**
- [ ] **문서 — README.md 오래됨**
- [ ] **인프라 — lint가 PR에서만 실행**

---

| 우선순위 | 개수 |
|---------|------|
| **CRITICAL** | 4 |
| **HIGH** | 8 |
| **MEDIUM** | 27 |
| **LOW** | 7 |
| **합계** | **46** |
