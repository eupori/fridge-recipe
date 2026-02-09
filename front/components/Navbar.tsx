"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { ChefHat, Heart, LogOut, User, Package, History } from "lucide-react";

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  // 로그인/회원가입 페이지에서는 간소화된 Navbar
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  return (
    <nav className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container max-w-4xl mx-auto px-4">
        <div className="flex h-14 items-center justify-between">
          {/* 로고 */}
          <Link href="/" className="flex items-center gap-2 font-bold text-lg hover:opacity-80 transition-opacity">
            <ChefHat className="w-6 h-6" />
            <span className="hidden sm:inline">냉장고 레시피</span>
          </Link>

          {/* 네비게이션 링크 & 인증 */}
          {!isAuthPage && (
            <div className="flex items-center gap-1 sm:gap-2">
              {/* Pantry 링크 */}
              <Button
                variant={pathname === "/pantry" ? "secondary" : "ghost"}
                size="sm"
                asChild
              >
                <Link href="/pantry">
                  <Package className="w-4 h-4 sm:mr-1" />
                  <span className="hidden sm:inline">보유 재료</span>
                </Link>
              </Button>

              {user ? (
                <>
                  {/* 최근 검색 */}
                  <Button
                    variant={pathname === "/history" ? "secondary" : "ghost"}
                    size="sm"
                    asChild
                  >
                    <Link href="/history">
                      <History className="w-4 h-4 sm:mr-1" />
                      <span className="hidden sm:inline">최근 검색</span>
                    </Link>
                  </Button>

                  {/* 즐겨찾기 */}
                  <Button
                    variant={pathname === "/favorites" ? "secondary" : "ghost"}
                    size="sm"
                    asChild
                  >
                    <Link href="/favorites">
                      <Heart className="w-4 h-4 sm:mr-1" />
                      <span className="hidden sm:inline">즐겨찾기</span>
                    </Link>
                  </Button>

                  {/* 로그아웃 */}
                  <Button variant="ghost" size="sm" onClick={logout}>
                    <LogOut className="w-4 h-4 sm:mr-1" />
                    <span className="hidden sm:inline">로그아웃</span>
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href="/login">
                      <User className="w-4 h-4 sm:mr-1" />
                      <span className="hidden sm:inline">로그인</span>
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link href="/signup">회원가입</Link>
                  </Button>
                </>
              )}
            </div>
          )}

          {/* 인증 페이지에서는 홈 링크만 */}
          {isAuthPage && (
            <Button variant="ghost" size="sm" asChild>
              <Link href="/">홈으로</Link>
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
}
