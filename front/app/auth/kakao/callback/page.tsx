"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { kakaoLogin } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function KakaoCallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkAuth } = useAuth();
  const [error, setError] = useState("");
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const savedState = sessionStorage.getItem("kakao_oauth_state");
    const returnUrl = sessionStorage.getItem("kakao_return_url") || "/";

    // cleanup
    sessionStorage.removeItem("kakao_oauth_state");
    sessionStorage.removeItem("kakao_return_url");

    if (!code) {
      setError("인가 코드가 없습니다.");
      return;
    }

    if (state && savedState && state !== savedState) {
      setError("보안 검증에 실패했습니다.");
      return;
    }

    const redirectUri = `${window.location.origin}/auth/kakao/callback`;

    (async () => {
      try {
        await kakaoLogin(code, redirectUri);
        await checkAuth();
        router.replace(returnUrl);
      } catch (err: any) {
        setError(err.message || "카카오 로그인에 실패했습니다.");
      }
    })();
  }, []);

  if (error) {
    return (
      <main className="container max-w-md mx-auto py-16 px-4 text-center">
        <div className="p-4 bg-destructive/10 text-destructive rounded-md mb-4">
          {error}
        </div>
        <button onClick={() => router.push("/login")} className="text-primary hover:underline">
          로그인 페이지로 돌아가기
        </button>
      </main>
    );
  }

  return (
    <main className="container max-w-md mx-auto py-16 px-4 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full" />
        <p className="text-muted-foreground">카카오 로그인 처리 중...</p>
      </div>
    </main>
  );
}

export default function KakaoCallbackPage() {
  return (
    <Suspense fallback={
      <main className="container max-w-md mx-auto py-16 px-4 text-center">
        <p className="text-muted-foreground">로딩 중...</p>
      </main>
    }>
      <KakaoCallbackHandler />
    </Suspense>
  );
}
