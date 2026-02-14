"use client";

import { Suspense, useMemo, useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { createRecommendation, getSearchHistories, getStats, SearchHistoryResponse, StatsResponse, RateLimitError } from "../lib/api";
import { useAuth } from "@/lib/auth-context";
import { usePersistedState } from "@/hooks/usePersistedState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChefHat, Clock, Users, Utensils, Loader2, Package, History, RefreshCw, ChevronRight, User, SlidersHorizontal, ChevronDown, ChevronUp, AlertCircle, LogIn, X } from "lucide-react";
import RecipeLoadingOverlay from "@/components/RecipeLoadingOverlay";
import { Onboarding } from "@/components/Onboarding";
import AdUnit from "@/components/AdUnit";
import { formatRelativeTime } from "@/lib/format";

export default function HomePage() {
  return (
    <Suspense fallback={<HomePageLoading />}>
      <HomePageContent />
    </Suspense>
  );
}

function HomePageLoading() {
  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-4">
          <ChefHat className="w-10 h-10 text-primary" />
          <h1 className="text-4xl font-bold">냉장고 재료만 알려주세요</h1>
        </div>
        <p className="text-2xl font-semibold text-primary mb-2">
          15분 레시피를 만들어드려요
        </p>
        <p className="text-muted-foreground">
          AI가 당신의 재료로 만들 수 있는 레시피 3개와 장보기 리스트를 자동으로 정리해줍니다
        </p>
      </div>
      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>재료 입력</CardTitle>
          <CardDescription>냉장고에 있는 재료를 알려주세요</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="animate-pulse space-y-4">
            <div className="h-32 bg-muted rounded" />
            <div className="h-10 bg-muted rounded" />
            <div className="h-12 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

function HomePageContent() {
  const { user, loading: authLoading } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [ingredientsText, setIngredientsText] = usePersistedState("recipe-ingredients", "계란, 김치, 양파");
  const [excludeText, setExcludeText] = usePersistedState("recipe-exclude", "");
  const [timeLimit, setTimeLimit] = usePersistedState("recipe-time-limit", 15);
  const [servings, setServings] = usePersistedState("recipe-servings", 1);
  const [tools, setTools] = usePersistedState<string[]>("recipe-tools", ["프라이팬"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pantryItems, setPantryItems] = useState<string[]>([]);
  const [recentHistories, setRecentHistories] = useState<SearchHistoryResponse[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [dailyRemaining, setDailyRemaining] = useState<number | null>(null);
  const [rateLimited, setRateLimited] = useState(false);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [showLoginBanner, setShowLoginBanner] = useState(false);

  // 비로그인 배너 표시 여부
  useEffect(() => {
    if (authLoading) return;
    if (!user && !sessionStorage.getItem("login-banner-dismissed")) {
      setShowLoginBanner(true);
    }
  }, [user, authLoading]);

  // 통계 로드
  useEffect(() => {
    getStats().then((s) => {
      if (s.total_recipes_generated > 0) setStats(s);
    });
  }, []);

  // Pantry 재료 로드
  useEffect(() => {
    try {
      const stored = localStorage.getItem("pantry-items");
      if (stored) {
        setPantryItems(JSON.parse(stored));
      }
    } catch {
      // ignore
    }
  }, []);

  // 최근 검색 기록 로드 (로그인 사용자만)
  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setRecentHistories([]);
      return;
    }

    getSearchHistories(3)
      .then(setRecentHistories)
      .catch(() => setRecentHistories([]));
  }, [user, authLoading]);

  // Pantry에서 재료 불러오기 (기존 입력에 추가)
  const loadFromPantry = () => {
    if (pantryItems.length === 0) return;

    // 현재 입력된 재료와 pantry 재료 합치기 (중복 제거)
    const currentIngredients = ingredientsText
      .split(/,|\n/)
      .map((s) => s.trim())
      .filter(Boolean);

    const combined = Array.from(new Set([...pantryItems, ...currentIngredients]));
    setIngredientsText(combined.join(", "));
  };

  // 검색 기록에서 재료 불러오기 (다시 검색) - 바로 검색 실행
  const loadFromHistory = async (history: SearchHistoryResponse) => {
    // 폼 상태 업데이트 (UI 반영용)
    setIngredientsText(history.ingredients.join(", "));
    setTimeLimit(history.time_limit_min);
    setServings(history.servings);

    // 바로 검색 실행 (history 값 직접 사용)
    setError(null);
    setRateLimited(false);
    setLoading(true);
    try {
      const rec = await createRecommendation({
        ingredients: history.ingredients,
        constraints: {
          time_limit_min: history.time_limit_min,
          servings: history.servings,
          tools,
          exclude: [],
        },
      });
      if (rec._dailyRemaining !== undefined) {
        setDailyRemaining(rec._dailyRemaining);
      }
      router.push(`/r/${rec.id}`);
    } catch (e: any) {
      if (e instanceof RateLimitError) {
        setRateLimited(true);
        setDailyRemaining(0);
        setError(e.message);
      } else {
        setError(e?.message ?? "요청에 실패했습니다");
      }
      setLoading(false);
    }
  };

  const ingredients = useMemo(() => {
    return ingredientsText
      .split(/,|\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [ingredientsText]);

  // onSubmit을 useCallback으로 정의하여 autoSearch useEffect에서 사용
  const onSubmit = useCallback(async () => {
    setError(null);
    setRateLimited(false);
    setLoading(true);
    try {
      const exclude = excludeText
        .split(/,|\n/)
        .map((s) => s.trim())
        .filter(Boolean);

      const rec = await createRecommendation({
        ingredients,
        constraints: {
          time_limit_min: timeLimit,
          servings,
          tools,
          exclude,
        },
      });

      // 남은 횟수 업데이트
      if (rec._dailyRemaining !== undefined) {
        setDailyRemaining(rec._dailyRemaining);
      }

      router.push(`/r/${rec.id}`);
    } catch (e: any) {
      if (e instanceof RateLimitError) {
        setRateLimited(true);
        setDailyRemaining(0);
        setError(e.message);
      } else {
        setError(e?.message ?? "요청에 실패했습니다");
      }
    } finally {
      setLoading(false);
    }
  }, [excludeText, ingredients, timeLimit, servings, tools]);

  // autoSearch 파라미터가 있으면 자동으로 검색 실행
  useEffect(() => {
    const autoSearch = searchParams.get("autoSearch");
    if (autoSearch === "true" && ingredients.length > 0 && !loading) {
      // URL에서 파라미터 제거
      router.replace("/", { scroll: false });
      // 검색 실행
      onSubmit();
    }
  }, [searchParams, ingredients, loading, router, onSubmit]);

  function toggleTool(t: string) {
    setTools((prev) => {
      // "상관없음" 클릭 시 → 다른 모든 도구 해제하고 "상관없음"만 선택
      if (t === "상관없음") {
        return prev.includes("상관없음") ? [] : ["상관없음"];
      }
      // 다른 도구 클릭 시 → "상관없음" 해제
      const withoutAny = prev.filter((x) => x !== "상관없음");
      if (withoutAny.includes(t)) {
        return withoutAny.filter((x) => x !== t);
      }
      return [...withoutAny, t];
    });
  }

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <Onboarding />
      <RecipeLoadingOverlay loading={loading} />
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-4">
          <ChefHat className="w-10 h-10 text-primary" />
          <h1 className="text-4xl font-bold">냉장고 재료만 알려주세요</h1>
        </div>
        <p className="text-2xl font-semibold text-primary mb-2">
          15분 레시피를 만들어드려요
        </p>
        <p className="text-muted-foreground">
          AI가 당신의 재료로 만들 수 있는 레시피 3개와 장보기 리스트를 자동으로 정리해줍니다
        </p>
        {stats && (
          <p className="text-sm text-muted-foreground mt-3">
            지금까지 <span className="font-semibold text-foreground">{stats.total_recipes_generated.toLocaleString()}개</span>의 레시피가 추천되었어요
            {stats.total_users > 0 && (
              <> · <span className="font-semibold text-foreground">{stats.total_users.toLocaleString()}명</span>의 사용자</>
            )}
          </p>
        )}
      </div>

      {showLoginBanner && !user && (
        <div className="mb-4 p-3 rounded-lg bg-primary/5 border border-primary/20 flex items-center gap-3">
          <div className="flex-1 text-sm">
            <span className="font-medium">로그인하면</span> 검색 기록 저장, 즐겨찾기, 무제한 검색을 이용할 수 있어요
          </div>
          <Button variant="outline" size="sm" asChild className="shrink-0">
            <Link href="/login">로그인</Link>
          </Button>
          <button
            onClick={() => {
              setShowLoginBanner(false);
              sessionStorage.setItem("login-banner-dismissed", "1");
            }}
            className="shrink-0 p-1 rounded-md hover:bg-muted transition-colors"
            aria-label="닫기"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      )}

      <Card className="shadow-lg">
        <CardHeader>
          <CardTitle>재료 입력</CardTitle>
          <CardDescription>냉장고에 있는 재료를 알려주세요</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="ingredients">재료</Label>
              {pantryItems.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={loadFromPantry}
                  disabled={loading}
                  className="h-7 text-xs"
                >
                  <Package className="w-3 h-3 mr-1" />
                  보유 재료 추가 ({pantryItems.length}개)
                </Button>
              )}
            </div>
            <Textarea
              id="ingredients"
              value={ingredientsText}
              onChange={(e) => setIngredientsText(e.target.value)}
              rows={5}
              placeholder="예: 계란, 김치, 양파&#10;두부"
              disabled={loading}
            />
            <p className="text-sm text-muted-foreground">
              인식된 재료: {ingredients.join(", ") || "(없음)"}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="time-limit" className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                시간 제한
              </Label>
              <Select value={timeLimit.toString()} onValueChange={(v) => setTimeLimit(Number(v))} disabled={loading}>
                <SelectTrigger id="time-limit">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10분</SelectItem>
                  <SelectItem value="15">15분</SelectItem>
                  <SelectItem value="20">20분</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="servings" className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                인분
              </Label>
              <Select value={servings.toString()} onValueChange={(v) => setServings(Number(v))} disabled={loading}>
                <SelectTrigger id="servings">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1인분</SelectItem>
                  <SelectItem value="2">2인분</SelectItem>
                  <SelectItem value="3">3인분</SelectItem>
                  <SelectItem value="4">4인분</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>상세 설정</span>
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {(tools.length > 0 && !tools.includes("상관없음") || excludeText.trim()) && (
              <span className="ml-auto text-xs text-primary">설정됨</span>
            )}
          </button>

          {showAdvanced && (
            <div className="space-y-4 pt-2 border-t">
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Utensils className="w-4 h-4" />
                  조리도구
                </Label>
                <div className="flex gap-2 flex-wrap">
                  {["프라이팬", "전자레인지", "에어프라이어", "냄비", "오븐", "상관없음"].map((t) => (
                    <Button
                      key={t}
                      type="button"
                      onClick={() => toggleTool(t)}
                      variant={tools.includes(t) ? "default" : "outline"}
                      size="sm"
                      disabled={loading}
                      aria-pressed={tools.includes(t)}
                    >
                      {t}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="exclude">제외 재료 / 알레르기</Label>
                <Input
                  id="exclude"
                  value={excludeText}
                  onChange={(e) => setExcludeText(e.target.value)}
                  placeholder="예: 우유, 땅콩"
                  disabled={loading}
                />
              </div>
            </div>
          )}

          {error && (
            <div className={`p-4 rounded-lg flex items-start gap-3 ${rateLimited ? "bg-primary/10" : "bg-destructive/10"}`}>
              {rateLimited ? (
                <LogIn className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
              )}
              <div>
                {rateLimited ? (
                  <>
                    <p className="text-sm font-medium mb-1">{error}</p>
                    <Button
                      variant="default"
                      size="sm"
                      className="mt-2 h-8"
                      asChild
                    >
                      <Link href="/login">
                        <LogIn className="w-3.5 h-3.5 mr-1.5" />
                        로그인하기
                      </Link>
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="text-sm font-medium text-destructive mb-1">
                      {error.includes("timeout") || error.includes("시간")
                        ? "요청 시간이 초과되었습니다"
                        : error.includes("network") || error.includes("fetch")
                        ? "네트워크 연결을 확인해주세요"
                        : "요청에 실패했습니다"}
                    </p>
                    <p className="text-xs text-destructive/80">{error}</p>
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-2 h-7 text-xs"
                      onClick={onSubmit}
                      disabled={loading}
                    >
                      <RefreshCw className="w-3 h-3 mr-1" />
                      다시 시도
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}

          {/* 데스크톱 CTA */}
          <div className="hidden sm:block">
            <Button
              onClick={onSubmit}
              disabled={loading || ingredients.length === 0}
              className="w-full h-12 text-base font-semibold"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  레시피 생성 중...
                </>
              ) : (
                "레시피 3개 추천받기"
              )}
            </Button>
          </div>

          {!user && dailyRemaining !== null && !rateLimited && (
            <p className="text-xs text-center text-muted-foreground">
              오늘 {dailyRemaining}회 남음 · 로그인하면 무제한
            </p>
          )}

          <p className="text-xs text-center text-muted-foreground">
            AI가 재료에 맞는 레시피를 생성합니다. 보유 재료를 등록하면 더 편리하게 이용할 수 있어요.
          </p>
        </CardContent>
      </Card>

      {/* 최근 검색 섹션 */}
      <Card className="mt-6 shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5" />
              <CardTitle className="text-lg">최근 검색</CardTitle>
            </div>
            {user && recentHistories.length > 0 && (
              <Button variant="ghost" size="sm" asChild className="text-muted-foreground">
                <Link href="/history">
                  전체 보기 <ChevronRight className="w-4 h-4 ml-1" />
                </Link>
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {!authLoading && !user ? (
            // 비로그인 상태
            <div className="text-center py-6">
              <User className="w-10 h-10 mx-auto mb-3 text-muted-foreground" />
              <p className="text-muted-foreground mb-4">
                로그인하면 검색 기록을 볼 수 있어요
              </p>
              <Button variant="outline" size="sm" asChild>
                <Link href="/login">로그인하기</Link>
              </Button>
            </div>
          ) : recentHistories.length === 0 ? (
            // 로그인했지만 기록 없음
            <div className="text-center py-6">
              <p className="text-muted-foreground">
                아직 검색 기록이 없습니다
              </p>
            </div>
          ) : (
            // 검색 기록 표시
            <div className="space-y-3">
              {recentHistories.map((history) => (
                <div
                  key={history.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="flex-1 min-w-0 mr-3">
                    <p className="font-medium truncate">
                      {history.ingredients.slice(0, 4).join(", ")}
                      {history.ingredients.length > 4 && ` 외 ${history.ingredients.length - 4}개`}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatRelativeTime(history.searched_at)}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => loadFromHistory(history)}
                    disabled={loading}
                    className="shrink-0"
                  >
                    <RefreshCw className="w-4 h-4 mr-1" />
                    다시 검색
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <AdUnit slot="4339934057" className="my-6" />

      {/* 모바일 하단 고정 CTA (BottomNav 위) */}
      <div className="fixed bottom-14 left-0 right-0 p-4 bg-background/95 backdrop-blur-sm border-t sm:hidden z-30">
        <Button
          onClick={onSubmit}
          disabled={loading || ingredients.length === 0}
          className="w-full h-12 text-base font-semibold"
          size="lg"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              레시피 생성 중...
            </>
          ) : (
            "레시피 3개 추천받기"
          )}
        </Button>
      </div>
      {/* 모바일 하단 CTA + BottomNav 공간 확보 */}
      <div className="h-28 sm:hidden" />
    </main>
  );
}
