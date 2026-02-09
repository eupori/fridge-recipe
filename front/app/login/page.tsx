"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const { checkAuth } = useAuth();

  // returnUrl 파라미터 (없으면 홈으로)
  const returnUrl = searchParams.get("returnUrl") || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      await checkAuth();
      router.push(returnUrl);
    } catch (err: any) {
      setError(err.message || "로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="text-center">
        <h1 className="text-2xl font-bold">로그인</h1>
        <p className="text-muted-foreground">냉장고 레시피에 로그인하세요</p>
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

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "로그인 중..." : "로그인"}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          계정이 없으신가요?{" "}
          <Link href={`/signup?returnUrl=${encodeURIComponent(returnUrl)}`} className="text-primary hover:underline">
            회원가입
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <main className="container max-w-md mx-auto py-16 px-4">
      <Suspense fallback={<div className="text-center text-muted-foreground">로딩 중...</div>}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
