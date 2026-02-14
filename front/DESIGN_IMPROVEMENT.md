# Design Improvement Plan

6인 페르소나 토론 결과를 기반으로 한 디자인 개선 계획.

- 김지훈 (30대 자취생), 박서연 (신혼부부), 최현수 (프론트엔드 개발자)
- 이수진 (서비스 디자이너), 한민지 (마케터), 정태영 (UX 기획자)

---

## Phase 1: 즉시 체감 (약 1시간)

### 1-1. 브랜드 컬러 시스템 (투표 6/6)

**파일**: `front/app/globals.css`

현재 shadcn 기본 그레이스케일 → "따뜻한 주방" 팔레트로 변경.

```css
:root {
  --background: 36 33% 97%;        /* #F9F7F4 따뜻한 크림 */
  --foreground: 24 10% 10%;        /* #1C1917 따뜻한 블랙 */
  --primary: 24 100% 50%;          /* #FF7A00 오렌지 */
  --primary-foreground: 0 0% 100%; /* 흰색 */
  --secondary: 36 20% 93%;         /* #F0EBE3 */
  --muted: 36 14% 93%;             /* #EEEBE5 */
  --muted-foreground: 24 5% 45%;   /* #756F67 */
  --border: 30 15% 88%;            /* #E2DDD6 */
  --input: 30 15% 88%;
  --ring: 24 100% 50%;
  --radius: 0.75rem;
}
```

색상 선택 근거:
- 오렌지: 식욕 자극. 배민(민트)/쿠팡이츠(청록)와 차별화
- 크림 배경: 순백보다 눈 편하고 따뜻함 전달
- radius 0.75rem: 음식 앱 특성상 부드러운 인상

### 1-2. 결과 페이지 ID 제거 + 첫 레시피 자동 펼침 (투표 6/6)

**파일**: `front/app/r/[id]/page.tsx`

- 225줄 `ID: {data.id}` 삭제
- 19줄 `useState<number | null>(null)` → `useState<number | null>(0)`

### 1-3. 한글 폰트 적용 (투표 5/6)

**파일**: `front/app/layout.tsx`, `front/tailwind.config.ts`

Noto Sans KR (Google Fonts, next/font로 자동 최적화)

```typescript
import { Noto_Sans_KR } from "next/font/google";
const notoSansKR = Noto_Sans_KR({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-noto",
});
```

### 1-4. 히어로 가치 제안 강화 + SEO title (투표 5/6)

**파일**: `front/app/page.tsx`, `front/app/layout.tsx`

변경 전:
```
오늘의 냉장고 레시피
재료를 입력하면 15분 내 가능한 레시피 3개와 장보기 리스트를 만들어줘요
```

변경 후:
```
냉장고 재료만 알려주세요
15분 레시피를 만들어드려요  ← primary 색상 강조
AI가 당신의 재료로 만들 수 있는 레시피 3개와 장보기 리스트를 자동으로 정리해줍니다
```

SEO title: "냉장고 레시피 | 재료로 15분 레시피 추천"

### 1-5. 접근성 개선 (투표 5/6)

**파일**: `front/app/r/[id]/page.tsx`, `front/app/page.tsx`, `front/components/RecipeLoadingOverlay.tsx`

- 상세보기 버튼: `aria-expanded` 추가
- 조리도구 토글: `aria-pressed` 추가
- 로딩 오버레이: `role="alert"` + `aria-live="assertive"` 추가
- 이미지: `loading="lazy"` + `decoding="async"` + `width`/`height` 추가

---

## Phase 2: 핵심 UX (약 3시간)

### 2-1. 모바일 하단 고정 CTA (투표 5/6)

**파일**: `front/app/page.tsx`

모바일에서 "레시피 추천받기" 버튼을 하단 고정. `sm:` 이상에서는 기존 위치 유지.
`pb-[calc(1rem+env(safe-area-inset-bottom))]`로 safe area 대응.

### 2-2. 폼 단순화 - 고급 옵션 접기 (투표 4/6)

**파일**: `front/app/page.tsx`

기본 노출: 재료 입력 + 시간/인분 (한 줄)
접기: 조리도구 + 제외재료 → "상세 설정" 토글

### 2-3. 빈 상태 + 에러 상태 컴포넌트화 (투표 5/6 + 4/6)

**새 파일**: `front/components/EmptyState.tsx`, `front/components/ErrorState.tsx`

빈 상태: 배경색 원형 아이콘 + 감정적 카피 + CTA 버튼
에러 상태: 유형별 분기 (네트워크/타임아웃/일반) + 재시도 버튼

### 2-4. 레시피 공유 버튼 (투표 4/6)

**새 파일**: `front/components/ShareButton.tsx`

Web Share API → clipboard fallback. 결과 페이지 FavoriteButton 옆에 배치.

---

## Phase 3: 앱 전환 대비 (약 7.5시간)

### 3-1. 모바일 바텀 탭 네비게이션 (투표 4/6)

**새 파일**: `front/components/BottomNav.tsx`

홈/보유재료/즐겨찾기/내정보 4탭. `sm:hidden`으로 모바일 전용.
React Native `createBottomTabNavigator`와 1:1 대응.

### 3-2. 결과 페이지 RSC 분리 + OG 메타태그

**파일**: `front/app/r/[id]/page.tsx` → Server + Client 하이브리드

`generateMetadata()`로 동적 OG 태그. 카카오톡/인스타 공유 시 이미지 미리보기.

### 3-3. TypeScript 타입 정의 (any 제거)

**새 파일**: `front/types/recommendation.ts`

`Recipe`, `ShoppingItem`, `Recommendation` 인터페이스 정의.

### 3-4. 조리 단계 체크리스트

**파일**: `front/app/r/[id]/page.tsx`

각 단계 클릭 시 완료 토글 + 진행률 표시.

### 3-5. formatRelativeTime 유틸리티 추출

**새 파일**: `front/lib/format.ts`

`page.tsx`와 `history/page.tsx`에서 중복 제거.

### 3-6. window.location.href → router.push

**파일**: `front/app/page.tsx`

전체 페이지 리로드 방지, SPA 내비게이션 유지.

---

## Phase 4: 성장 엔진 (앱 출시 전)

- 카카오톡 SDK 공유 연동
- 소프트 게이팅 (비회원 3회/일 제한)
- 온보딩 플로우
- 구독 업셀 터치포인트
- 사회적 증거 API (사용 통계)
- 다크 모드 QA

---

## 크로스 플랫폼 참고 (React Native 전환)

- CSS 변수 → `shared/tokens/colors.ts`로 추출하면 웹/앱 동일 값 사용
- 바텀 탭 → `@react-navigation/bottom-tabs`와 1:1 대응
- Noto Sans KR → `expo-font`로 동일 폰트 로드
- Web Share API → `react-native-share` 동일 패턴
- aria 속성 → `accessibilityRole`, `accessibilityState` 대응
