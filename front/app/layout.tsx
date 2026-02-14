import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Navbar } from "@/components/Navbar";
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "냉장고 레시피 | 재료로 15분 레시피 추천",
  description: "냉장고 재료만 입력하면 AI가 15분 안에 만들 수 있는 레시피 3개와 장보기 리스트를 자동으로 정리해줍니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <meta name="google-adsense-account" content="ca-pub-4539589433798899" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4539589433798899"
          crossOrigin="anonymous"
        />
      </head>
      <body className="font-noto antialiased pb-14 sm:pb-0">
        <AuthProvider>
          <Navbar />
          {children}
          <BottomNav />
        </AuthProvider>
      </body>
    </html>
  );
}
