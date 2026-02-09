import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";

export const metadata: Metadata = {
  title: "오늘의 냉장고 레시피 3개",
  description: "재료 입력하면 15분 레시피 3개 + 장보기 리스트",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="font-sans antialiased">
        <AuthProvider>
          <Navbar />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
