import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { RecipeJobProvider } from "@/lib/recipe-job-context";
import { Navbar } from "@/components/Navbar";
import { BottomNav } from "@/components/BottomNav";
import FloatingJobIndicator from "@/components/FloatingJobIndicator";
import RecipeReadyToast from "@/components/RecipeReadyToast";

export const metadata: Metadata = {
  metadataBase: new URL("https://recipe.eupori.dev"),
  title: "오머먹 - 냉장고 재료로 레시피 추천 | 오늘 뭐 먹지?",
  description: "냉장고에 있는 재료를 입력하면 15분 안에 만들 수 있는 레시피 3개를 AI가 추천해줍니다. 자취생, 1인가구를 위한 냉장고 파먹기 레시피.",
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
        {process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID && (
          <>
            <script
              async
              src={`https://www.googletagmanager.com/gtag/js?id=${process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID}`}
            />
            <script
              dangerouslySetInnerHTML={{
                __html: `window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag('js',new Date());gtag('config','${process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID}')`,
              }}
            />
          </>
        )}
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
