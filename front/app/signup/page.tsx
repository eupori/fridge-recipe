"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { signup, login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkAuth } = useAuth();

  // returnUrl 파라미터 (없으면 홈으로)
  const returnUrl = searchParams.get("returnUrl") || "/";

  function handleKakaoLogin(returnUrl: string) {
    const state = crypto.randomUUID();
    sessionStorage.setItem("kakao_oauth_state", state);
    sessionStorage.setItem("kakao_return_url", returnUrl);
    const redirectUri = `${window.location.origin}/auth/kakao/callback`;
    const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${process.env.NEXT_PUBLIC_KAKAO_REST_API_KEY}&redirect_uri=${encodeURIComponent(redirectUri)}&response_type=code&state=${state}`;
    window.location.href = kakaoAuthUrl;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setLoading(true);

    try {
      await signup(email, password);
      // 회원가입 성공 후 자동 로그인
      await login(email, password);
      await checkAuth();
      router.push(returnUrl);
    } catch (err: any) {
      setError(err.message || "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="text-center">
        <h1 className="text-2xl font-bold">회원가입</h1>
        <p className="text-muted-foreground">간편하게 가입하고 즐겨찾기를 저장하세요</p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">이메일</Label>
            <Input
              id="email"
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              type="password"
              placeholder="6자 이상"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">비밀번호 확인</Label>
            <Input
              id="confirmPassword"
              type="password"
              placeholder="비밀번호를 다시 입력하세요"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "가입 중..." : "회원가입"}
          </Button>
        </form>

        {/* 구분선 */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">또는</span>
          </div>
        </div>

        {/* 카카오 로그인 */}
        <button
          type="button"
          onClick={() => handleKakaoLogin(returnUrl)}
          className="w-full flex items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors hover:opacity-90"
          style={{ backgroundColor: "#FEE500", color: "#000000" }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 1C4.58 1 1 3.79 1 7.21c0 2.17 1.45 4.08 3.64 5.18-.16.57-.58 2.07-.66 2.39-.1.39.14.39.3.28.12-.08 1.95-1.32 2.74-1.86.63.09 1.28.14 1.98.14 4.42 0 8-2.79 8-6.21C17 3.79 13.42 1 9 1Z" fill="#000000"/>
          </svg>
          카카오로 시작하기
        </button>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          이미 계정이 있으신가요?{" "}
          <Link href={`/login?returnUrl=${encodeURIComponent(returnUrl)}`} className="text-primary hover:underline">
            로그인
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SignupPage() {
  return (
    <main className="container max-w-md mx-auto py-16 px-4">
      <Suspense fallback={<div className="text-center text-muted-foreground">로딩 중...</div>}>
        <SignupForm />
      </Suspense>
    </main>
  );
}
