import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context"; // GA4: G-K9DSYJ36D7
import { RecipeJobProvider } from "@/lib/recipe-job-context";
import { Navbar } from "@/components/Navbar";
import { BottomNav } from "@/components/BottomNav";
import FloatingJobIndicator from "@/components/FloatingJobIndicator";
import RecipeReadyToast from "@/components/RecipeReadyToast";

export const metadata: Metadata = {
  metadataBase: new URL("https://recipe.eupori.dev"),
  title: "냉탐정 - 냉장고 재료로 AI 레시피 추천 | 오늘 뭐 먹지?",
  description: "냉장고에 있는 재료를 입력하면 AI가 15분 레시피 3개와 장보기 리스트를 추천합니다. 자취생·1인가구를 위한 냉장고 파먹기 레시피 추천 서비스.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||((!t||t==='system')&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
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
        <script
          async
          src="https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js"
          crossOrigin="anonymous"
        />
        <script
          async
          src="https://www.googletagmanager.com/gtag/js?id=G-K9DSYJ36D7"
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','G-K9DSYJ36D7')`,
          }}
        />
      </head>
      <body className="font-noto antialiased pb-14 sm:pb-0">
        <AuthProvider>
          <RecipeJobProvider>
            <Navbar />
            {children}
            <BottomNav />
            <FloatingJobIndicator />
            <RecipeReadyToast />
          </RecipeJobProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
