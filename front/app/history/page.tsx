"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  getSearchHistories,
  deleteSearchHistory,
  clearAllSearchHistories,
  resolveImageUrl,
  SearchHistoryResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { History, Trash2, ChefHat, Search, ChevronRight, RefreshCw, Clock, Users } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";
import AdUnit from "@/components/AdUnit";

export default function HistoryPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [histories, setHistories] = useState<SearchHistoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      router.push("/login");
      return;
    }

    loadHistories();
  }, [user, authLoading, router]);

  const loadHistories = async () => {
    setLoading(true);
    try {
      const data = await getSearchHistories();
      setHistories(data);
    } catch (err: any) {
      setError(err.message || "검색 기록을 불러올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (historyId: string) => {
    try {
      await deleteSearchHistory(historyId);
      setHistories((prev) => prev.filter((h) => h.id !== historyId));
    } catch (err: any) {
      console.error("삭제 실패:", err);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("모든 검색 기록을 삭제하시겠습니까?")) return;

    setClearing(true);
    try {
      await clearAllSearchHistories();
      setHistories([]);
    } catch (err: any) {
      console.error("전체 삭제 실패:", err);
    } finally {
      setClearing(false);
    }
  };

  const handleSearchAgain = (history: SearchHistoryResponse) => {
    localStorage.setItem("recipe-ingredients", JSON.stringify(history.ingredients.join(", ")));
    localStorage.setItem("recipe-time-limit", JSON.stringify(history.time_limit_min));
    localStorage.setItem("recipe-servings", JSON.stringify(history.servings));
    router.push("/?autoSearch=true");
  };

  if (authLoading || loading) {
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <History className="w-6 h-6 shrink-0" />
            <h1 className="text-2xl sm:text-3xl font-bold">최근 검색 기록</h1>
          </div>
          <p className="text-sm text-muted-foreground">최근 7일간의 검색 기록입니다</p>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="overflow-hidden">
              <CardContent className="p-0">
                <div className="animate-pulse px-4 pt-4 pb-2">
                  <div className="h-5 bg-muted rounded w-3/4 mb-2" />
                  <div className="h-3 bg-muted rounded w-1/3" />
                </div>
                <div className="animate-pulse grid grid-cols-3 gap-px bg-border mx-4 my-2 rounded-lg overflow-hidden">
                  {[1, 2, 3].map((j) => (
                    <div key={j} className="bg-muted aspect-[2/1]" />
                  ))}
                </div>
                <div className="animate-pulse flex gap-2 px-4 pb-4 pt-2">
                  <div className="h-8 bg-muted rounded w-24" />
                  <div className="h-8 bg-muted rounded w-24" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="mb-8 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <History className="w-6 h-6 shrink-0" />
            <h1 className="text-2xl sm:text-3xl font-bold">최근 검색 기록</h1>
          </div>
          <p className="text-sm text-muted-foreground">최근 7일간의 검색 기록입니다</p>
        </div>

        {histories.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearAll}
            disabled={clearing}
            className="text-destructive hover:text-destructive shrink-0"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            <span className="hidden sm:inline">모두 삭제</span>
            <span className="sm:hidden">삭제</span>
          </Button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md mb-6">
          {error}
        </div>
      )}

      {histories.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Search className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">
              아직 검색 기록이 없습니다
            </p>
            <Button asChild>
              <Link href="/">레시피 추천받기</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {histories.map((history) => {
            const hasImages = history.recipe_images?.some((img) => img);
            return (
              <Card key={history.id} className="overflow-hidden">
                <CardContent className="p-0">
                  {/* 상단: 검색 조건 + 삭제 */}
                  <div className="flex items-start justify-between gap-2 px-4 pt-4 pb-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-base mb-1 truncate">
                        {history.ingredients.slice(0, 5).join(", ")}
                        {history.ingredients.length > 5 && ` 외 ${history.ingredients.length - 5}개`}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {history.time_limit_min}분
                        </span>
                        <span className="flex items-center gap-1">
                          <Users className="w-3 h-3" />
                          {history.servings}인분
                        </span>
                        <span>{formatRelativeTime(history.searched_at)}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(history.id)}
                      className="text-muted-foreground hover:text-destructive shrink-0 -mt-1 -mr-2 h-8 w-8"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>

                  {/* 중앙: 레시피 결과 미리보기 */}
                  {hasImages ? (
                    <div className="grid grid-cols-3 gap-px bg-border mx-4 my-2 rounded-lg overflow-hidden">
                      {history.recipe_titles.map((title, idx) => {
                        const imgUrl = resolveImageUrl(history.recipe_images?.[idx]);
                        return (
                          <div key={idx} className="relative bg-muted aspect-[2/1]">
                            {imgUrl ? (
                              <img
                                src={imgUrl}
                                alt={title}
                                className="w-full h-full object-cover"
                                loading="lazy"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <ChefHat className="w-5 h-5 text-muted-foreground/30" />
                              </div>
                            )}
                            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent px-1.5 pb-1 pt-4">
                              <p className="text-[11px] text-white font-medium truncate">{title}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex gap-1.5 px-4 my-2">
                      {history.recipe_titles.map((title, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-1.5 px-2.5 py-1 bg-muted rounded-full text-xs min-w-0"
                        >
                          <ChefHat className="w-3 h-3 text-muted-foreground shrink-0" />
                          <span className="truncate">{title}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 하단: 액션 버튼 */}
                  <div className="flex items-center gap-2 px-4 pb-4 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSearchAgain(history)}
                      className="flex-1 sm:flex-none"
                    >
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                      다시 검색
                    </Button>
                    <Button variant="default" size="sm" asChild className="flex-1 sm:flex-none whitespace-nowrap">
                      <Link href={`/r/${history.recommendation_id}`} className="inline-flex items-center">
                        결과 보기
                        <ChevronRight className="w-3.5 h-3.5 ml-1 shrink-0" />
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
      <AdUnit slot="7845903215" className="mt-6" />
    </main>
  );
}
