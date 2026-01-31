import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "오늘의 냉장고 레시피 3개",
  description: "재료 입력하면 15분 레시피 3개 + 장보기 리스트",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body style={{ fontFamily: "system-ui, -apple-system, Segoe UI, Roboto" }}>{children}</body>
    </html>
  );
}
