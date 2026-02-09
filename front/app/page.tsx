"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { createRecommendation, getSearchHistories, SearchHistoryResponse } from "../lib/api";
import { useAuth } from "@/lib/auth-context";
import { usePersistedState } from "@/hooks/usePersistedState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChefHat, Clock, Users, Utensils, Loader2, Package, History, RefreshCw, ChevronRight, User } from "lucide-react";

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "방금 전";
  if (diffMins < 60) return `${diffMins}분 전`;
  if (diffHours < 24) return `${diffHours}시간 전`;
  if (diffDays === 1) return "어제";
  if (diffDays < 7) return `${diffDays}일 전`;

  return date.toLocaleDateString("ko-KR", {
    month: "long",
    day: "numeric",
  });
}

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const [ingredientsText, setIngredientsText] = usePersistedState("recipe-ingredients", "계란, 김치, 양파");
  const [excludeText, setExcludeText] = usePersistedState("recipe-exclude", "");
  const [timeLimit, setTimeLimit] = usePersistedState("recipe-time-limit", 15);
  const [servings, setServings] = usePersistedState("recipe-servings", 1);
  const [tools, setTools] = usePersistedState<string[]>("recipe-tools", ["프라이팬"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pantryItems, setPantryItems] = useState<string[]>([]);
  const [recentHistories, setRecentHistories] = useState<SearchHistoryResponse[]>([]);

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

  // 검색 기록에서 재료 불러오기 (다시 검색)
  const loadFromHistory = (history: SearchHistoryResponse) => {
    setIngredientsText(history.ingredients.join(", "));
    setTimeLimit(history.time_limit_min);
    setServings(history.servings);
  };

  const ingredients = useMemo(() => {
    return ingredientsText
      .split(/,|\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }, [ingredientsText]);

  async function onSubmit() {
    setError(null);
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

      window.location.href = `/r/${rec.id}`;
    } catch (e: any) {
      setError(e?.message ?? "요청에 실패했습니다");
    } finally {
      setLoading(false);
    }
  }

  function toggleTool(t: string) {
    setTools((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));
  }

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-2 mb-4">
          <ChefHat className="w-10 h-10" />
          <h1 className="text-4xl font-bold">오늘의 냉장고 레시피</h1>
        </div>
        <p className="text-muted-foreground text-lg">
          재료를 입력하면 15분 내 가능한 레시피 3개와 장보기 리스트를 만들어줘요
        </p>
      </div>

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

          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Utensils className="w-4 h-4" />
              조리도구
            </Label>
            <div className="flex gap-2 flex-wrap">
              {["프라이팬", "전자레인지", "에어프라이어"].map((t) => (
                <Button
                  key={t}
                  type="button"
                  onClick={() => toggleTool(t)}
                  variant={tools.includes(t) ? "default" : "outline"}
                  size="sm"
                  disabled={loading}
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

          {error && (
            <div className="p-4 bg-destructive/10 text-destructive rounded-md text-sm">
              {error}
            </div>
          )}

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
    </main>
  );
}
