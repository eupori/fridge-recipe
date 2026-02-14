"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  getSearchHistories,
  deleteSearchHistory,
  clearAllSearchHistories,
  SearchHistoryResponse,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { History, Trash2, ChefHat, Search, ExternalLink, RefreshCw } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";

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
    // 재료를 localStorage에 저장하고 메인 페이지로 이동 (자동 검색 트리거)
    localStorage.setItem("recipe-ingredients", JSON.stringify(history.ingredients.join(", ")));
    localStorage.setItem("recipe-time-limit", JSON.stringify(history.time_limit_min));
    localStorage.setItem("recipe-servings", JSON.stringify(history.servings));
    router.push("/?autoSearch=true");
  };

  if (authLoading || loading) {
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <p className="text-muted-foreground">불러오는 중...</p>
      </main>
    );
  }

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <History className="w-6 h-6" />
            <h1 className="text-3xl font-bold">최근 검색 기록</h1>
          </div>
          <p className="text-muted-foreground">최근 7일간의 검색 기록입니다</p>
        </div>

        {histories.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearAll}
            disabled={clearing}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            모두 삭제
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
        <div className="space-y-4">
          {histories.map((history) => (
            <Card key={history.id} className="overflow-hidden">
              <CardContent className="p-4">
                {/* 검색 조건 */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <p className="font-medium text-lg mb-1">
                      {history.ingredients.slice(0, 5).join(", ")}
                      {history.ingredients.length > 5 && ` 외 ${history.ingredients.length - 5}개`}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {history.time_limit_min}분 / {history.servings}인분 / {formatRelativeTime(history.searched_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDelete(history.id)}
                    className="text-muted-foreground hover:text-destructive shrink-0"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                {/* 레시피 결과 미리보기 */}
                <div className="flex gap-2 mb-4 overflow-x-auto">
                  {history.recipe_titles.map((title, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 shrink-0 px-3 py-1.5 bg-muted rounded-full text-sm"
                    >
                      <ChefHat className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="whitespace-nowrap">{title}</span>
                    </div>
                  ))}
                </div>

                {/* 액션 버튼 */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSearchAgain(history)}
                  >
                    <RefreshCw className="w-4 h-4 mr-1" />
                    다시 검색
                  </Button>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/r/${history.recommendation_id}`}>
                      <ExternalLink className="w-4 h-4 mr-1" />
                      결과 보기
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
