# 개선 체크리스트 (2026-02-16)

## CRITICAL (즉시 수정)

- [x] **보안 — JWT 시크릿 하드코딩** `config.py:15` — EC2에 64자 랜덤 hex 설정 완료
- [x] **보안 — CORS + credentials 위반** `main.py:61-68` — `or ["*"]` 폴백 제거
- [x] **Git — `back/data/` 미제외** — `.gitignore`에 추가, git 추적 제거
- [x] **인프라 — `.env.production` 커밋됨** — git 추적 제거 (Vercel 대시보드에서 관리)

## HIGH (이번 주 수정)

- [x] **보안 — IP 스푸핑 취약** `recommendations.py:85` — `x-real-ip` 헤더로 변경
- [x] **보안 — 인증 사용자 레이트 리밋 없음** — 로그인 30회/일 제한 추가
- [x] **DB — UsageService 레이스 컨디션** `usage_service.py:33-53` — PostgreSQL UPSERT 적용
- [x] **인프라 — Docker 헬스체크 없음** `docker-compose.yml` — 헬스체크 추가
- [x] **인프라 — 배포 후 검증 없음** `deploy-backend.yml` — health check step 추가
- [x] **인프라 — Nginx 보안 헤더 미설정** — X-Content-Type-Options, X-Frame-Options 등 추가
- [x] **프론트 — TypeScript strict 모드 OFF** `tsconfig.json` — strict: true (에러 0)
- [ ] **테스트 — 자동화 테스트 전무**

## MEDIUM — SEO/마케팅

- [ ] **SEO — JSON-LD 구조화 데이터 없음** `ResultClient.tsx`
- [ ] **SEO — OG 이미지 없음** `layout.tsx`
- [x] **SEO — Twitter 카드 태그 누락** `r/[id]/page.tsx` — twitter 메타 추가
- [x] **SEO — canonical 링크 없음** `r/[id]/page.tsx` — alternates.canonical 추가

## MEDIUM — 성능

- [ ] **성능 — React.memo 미적용** `ShareButton.tsx`, `FavoriteButton.tsx`
- [ ] **성능 — 이미지 캐시 크기 제한 없음** `image_search_service.py`
- [ ] **성능 — 통계 API 캐싱 없음** `page.tsx:90-94`
- [x] **성능 — Nginx gzip 미설정** — gzip on 추가
- [x] **성능 — DB 인덱스 누락** `favorite.py` — recommendation_id 인덱스 추가

## MEDIUM — UX

- [x] **UX — BottomNav "내정보" 라벨 오해** `BottomNav.tsx:11` — 로그인 상태별 분기
- [x] **UX — 즐겨찾기 빈 화면에 CTA 없음** `favorites/page.tsx:85` — 이미 구현되어 있음
- [x] **UX — 모바일 터치 타겟 부족** `ShareButton.tsx` — 36px → 44px 확대
- [x] **UX — iOS safe-area 미대응** `page.tsx:603-621` — env(safe-area-inset-bottom) 적용
- [x] **UX — 온보딩 ESC 키 미지원** `Onboarding.tsx` — keydown 이벤트 추가

## MEDIUM — 접근성

- [x] **접근성 — 재료 색상 구분만 사용** `ResultClient.tsx:352-364` — 텍스트 라벨 강화 + aria-hidden
- [x] **접근성 — 조리 단계 키보드 조작 불가** `ResultClient.tsx:470` — role=checkbox, Enter/Space 지원
- [ ] **접근성 — 폼 라벨 미연결** `page.tsx:437-445`

## MEDIUM — 코드 품질

- [x] **코드 — resolveImageUrl 중복 정의** `r/[id]/page.tsx` + `lib/api.ts` — lib/api.ts에서 import
- [x] **코드 — API_BASE 재정의** `r/[id]/page.tsx:4-5` — API_ROOT 재정의 제거
- [x] **코드 — 에러 메시지 문자열 비교** `page.tsx:475` — toLowerCase + 추가 패턴
- [ ] **코드 — 매직 스트링 산재**
- [ ] **코드 — 에러 메시지 언어 비일관**

## MEDIUM — 인프라

- [ ] **인프라 — 배포 롤백 전략 없음** `deploy-backend.yml`
- [ ] **인프라 — Docker 빌드 캐시 비활성**
- [x] **인프라 — Docker non-root 실행 안 함** `Dockerfile` — appuser 생성 및 적용
- [ ] **인프라 — 요청 ID 추적 없음**
- [ ] **모니터링 — CloudWatch 알람 없음**

## LOW (여유 시 개선)

- [ ] **UX — 히스토리 로딩 스켈레톤 없음**
- [ ] **UX — 팬트리 삭제 Undo 없음**
- [ ] **UX — 모바일 로고 텍스트 숨김** `Navbar.tsx:45`
- [ ] **성능 — Sentry Session Replay 비활성**
- [ ] **코드 — localStorage 키 상수화**
- [x] **문서 — README.md 오래됨** — 포트폴리오용 업데이트 완료
- [ ] **인프라 — lint가 PR에서만 실행**

---

| 우선순위 | 전체 | 완료 | 잔여 |
|---------|------|------|------|
| **CRITICAL** | 4 | 4 | 0 |
| **HIGH** | 8 | 7 | 1 |
| **MEDIUM** | 27 | 17 | 10 |
| **LOW** | 7 | 1 | 6 |
| **합계** | **46** | **29** | **17** |
