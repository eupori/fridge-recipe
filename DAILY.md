# DAILY — 일일 작업 기록

## 2026-02-12

### 완료
- [x] 풀스크린 로딩 오버레이 (진행 단계 표시 + 요리 팁 애니메이션)
- [x] Google 애드센스 설정 (ads.txt, 메타태그, 스크립트)
- [x] 도메인 설정 (`eupori.dev` + `recipe.eupori.dev` → Vercel front 프로젝트)
- [x] robots.txt 추가 (크롤러 접근 허용)
- [x] .gitignore 정리 (빌드 캐시, 설정 파일 제외)
- [x] 불필요 파일 삭제 (DIVERSITY_IMPROVEMENT.md, landing/)

### 이슈/메모
- 애드센스 승인 대기 중 (ads.txt "찾을 수 없음" → 크롤러 재방문 필요)
- `back/data/image_cache.json` 90MB → Git LFS 또는 .gitignore 추가 필요
- 프론트 배포는 수동 (`vercel --prod --yes`), 자동배포 미설정

---

## 2026-02-11

### 완료
- [x] API Gateway 30초 타임아웃 해결 (비동기 이미지 로딩)
- [x] 503 타임아웃 수정 (recommendations 엔드포인트)
- [x] Lambda cold start 시 자동 테이블 생성
- [x] Gemini 이미지 100KB 압축 (Lambda payload 제한 대응)
- [x] 이미지 제공자 gemini → mock 전환 (payload 제한 임시 대응)

---

## 2026-02-10

### 완료
- [x] AWS Lambda 배포 설정 (SAM + Docker)
- [x] GitHub Actions CI/CD 워크플로우
- [x] 커스텀 도메인 설정 (`recipe-api.eupori.dev`)
- [x] PostgreSQL (Supabase) 연동
- [x] psycopg2-binary 호환성 수정
- [x] ESLint 설정

---

## 2026-02-09

### 완료
- [x] 검색 기록 + 즐겨찾기 시스템 개선
- [x] 공통 Navbar 컴포넌트
- [x] Pantry (보유 재료 관리)
- [x] 레시피 좋아요(즐겨찾기) 시스템
- [x] 최근 검색 기록 7일 보관
- [x] 장보기 목록에서 보유재료로 바로 추가
- [x] 즐겨찾기 중복 등록 버그 수정
