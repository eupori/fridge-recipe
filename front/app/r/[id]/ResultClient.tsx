"use client";

import { useEffect, useState } from "react";
import { getRecommendation, addFavorite, getRecipeLikeStats, getRecipeImages, resolveImageUrl, RecommendationLikeStats } from "../../../lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Clock, Users, ChefHat, ShoppingCart, Lightbulb, ChevronDown, ChevronUp, Plus, Check, ExternalLink, CircleCheck } from "lucide-react";
import { FavoriteButton } from "@/components/FavoriteButton";
import { ShareButton } from "@/components/ShareButton";
import AdUnit from "@/components/AdUnit";
import { useAuth } from "@/lib/auth-context";
import type { Recommendation, Recipe, ShoppingItem } from "@/types/recommendation";

const PANTRY_STORAGE_KEY = "pantry-items";

export default function ResultClient({ id }: { id: string }) {
  const [data, setData] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0);
  const [likeStats, setLikeStats] = useState<RecommendationLikeStats | null>(null);
  const [pantryItems, setPantryItems] = useState<string[]>([]);
  const [recipeImages, setRecipeImages] = useState<(string | null)[]>([]);
  const [imageLoading, setImageLoading] = useState<boolean[]>([]);
  const [completedSteps, setCompletedSteps] = useState<Record<number, Set<number>>>({});
  const { user } = useAuth();

  // 보유 재료 로드
  useEffect(() => {
    try {
      const stored = localStorage.getItem(PANTRY_STORAGE_KEY);
      if (stored) {
        setPantryItems(JSON.parse(stored));
      }
    } catch {
      // ignore
    }
  }, []);

  // 보유 재료에 추가
  const addToPantry = (item: string) => {
    const trimmed = item.trim();
    if (!trimmed || pantryItems.includes(trimmed)) return;

    const updated = [...pantryItems, trimmed];
    setPantryItems(updated);
    localStorage.setItem(PANTRY_STORAGE_KEY, JSON.stringify(updated));
  };

  // 보유 재료 여부 확인
  const isInPantry = (item: string) => {
    return pantryItems.includes(item.trim());
  };

  useEffect(() => {
    (async () => {
      try {
        const [rec, stats] = await Promise.all([
          getRecommendation(id),
          getRecipeLikeStats(id),
        ]);
        setData(rec);
        setLikeStats(stats);
      } catch (e: any) {
        setError(e?.message ?? "불러오기에 실패했습니다");
      }
    })();
  }, [id]);

  // 이미지가 없는 레시피에 대해 비동기로 이미지 로드
  useEffect(() => {
    if (!data?.recipes) return;

    const recipes = data.recipes;
    setRecipeImages(recipes.map((r: Recipe) => resolveImageUrl(r.image_url)));

    const missingRecipes = recipes
      .map((r: Recipe, i: number) => (!r.image_url ? { index: i, title: r.title } : null))
      .filter((x): x is { index: number; title: string } => x !== null);

    if (missingRecipes.length === 0) return;

    const missingSet = new Set(missingRecipes.map((m) => m.index));
    setImageLoading(recipes.map((_, i) => missingSet.has(i)));

    (async () => {
      const titles = missingRecipes.map((m) => m.title);
      const results = await getRecipeImages(titles, data.id);
      const imageMap = new Map(results.map((r) => [r.title, resolveImageUrl(r.image_url)]));

      setRecipeImages((prev) => {
        const next = [...prev];
        for (const { index, title } of missingRecipes) {
          next[index] = imageMap.get(title) ?? null;
        }
        return next;
      });
      setImageLoading(recipes.map(() => false));
    })();
  }, [data]);

  // 로그인 후 pendingFavorite 자동 처리
  const [pendingProcessed, setPendingProcessed] = useState<{recipeIndex: number} | null>(null);

  useEffect(() => {
    const processPendingFavorite = async () => {
      if (!user) return;

      const pendingStr = localStorage.getItem("pendingFavorite");
      if (!pendingStr) return;

      try {
        const pending = JSON.parse(pendingStr);

        if (Date.now() - pending.timestamp > 10 * 60 * 1000) {
          localStorage.removeItem("pendingFavorite");
          return;
        }

        if (pending.recommendationId === id) {
          try {
            await addFavorite(
              pending.recommendationId,
              pending.recipeIndex,
              pending.recipeTitle,
              pending.recipeImageUrl
            );
            handleFavoriteChange(pending.recipeIndex, true);
            setPendingProcessed({ recipeIndex: pending.recipeIndex });
          } catch (err: any) {
            if (err.message?.includes("이미 즐겨찾기")) {
              setPendingProcessed({ recipeIndex: pending.recipeIndex });
            }
          }
          localStorage.removeItem("pendingFavorite");
        }
      } catch (e) {
        localStorage.removeItem("pendingFavorite");
      }
    };

    processPendingFavorite();
  }, [user, id]);

  const toggleExpand = (idx: number) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  const toggleStep = (recipeIdx: number, stepIdx: number) => {
    setCompletedSteps((prev) => {
      const current = new Set(prev[recipeIdx] || []);
      if (current.has(stepIdx)) {
        current.delete(stepIdx);
      } else {
        current.add(stepIdx);
      }
      return { ...prev, [recipeIdx]: current };
    });
  };

  const getStepProgress = (recipeIdx: number, totalSteps: number): number => {
    const completed = completedSteps[recipeIdx]?.size || 0;
    return totalSteps > 0 ? Math.round((completed / totalSteps) * 100) : 0;
  };

  const getLikeCountForRecipe = (recipeIndex: number): number => {
    if (!likeStats) return 0;
    const recipe = likeStats.recipes.find((r) => r.recipe_index === recipeIndex);
    return recipe?.like_count ?? 0;
  };

  const handleFavoriteChange = (recipeIndex: number, isFavorite: boolean) => {
    setLikeStats((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        recipes: prev.recipes.map((r) =>
          r.recipe_index === recipeIndex
            ? { ...r, like_count: r.like_count + (isFavorite ? 1 : -1) }
            : r
        ),
      };
    });
  };

  if (error) {
    const isNotFound = error.includes("not_found") || error.includes("404");
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <Card>
          <CardContent className="py-12 text-center">
            <ChefHat className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            {isNotFound ? (
              <>
                <h2 className="text-xl font-bold mb-2">레시피를 찾을 수 없습니다</h2>
                <p className="text-muted-foreground mb-6">
                  서버가 재시작되어 이전 검색 결과가 사라졌습니다.<br />
                  동일한 재료로 다시 검색해보세요.
                </p>
              </>
            ) : (
              <>
                <h2 className="text-xl font-bold mb-2">오류가 발생했습니다</h2>
                <p className="text-muted-foreground mb-6">{error}</p>
              </>
            )}
            <Button asChild>
              <a href="/">새로 검색하기</a>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <p className="text-muted-foreground">불러오는 중…</p>
      </main>
    );
  }

  return (
    <main className="container max-w-4xl mx-auto py-10 px-4">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <ChefHat className="w-6 h-6" />
          <h1 className="text-3xl font-bold">추천 레시피</h1>
        </div>
      </div>

      <div className="space-y-4 mb-8">
        {data.recipes?.map((r: Recipe, idx: number) => {
          const isExpanded = expandedIdx === idx;
          const steps = r.steps || [];
          const progress = getStepProgress(idx, steps.length);
          const recipeCompleted = completedSteps[idx]?.size || 0;

          return (
            <Card key={idx} className="overflow-hidden">
              {/* 메인 영역: 이미지 + 핵심 정보 */}
              <div className="flex">
                {/* 좌측: 이미지 */}
                {(() => {
                  const imageUrl = recipeImages[idx];
                  const isLoading = imageLoading[idx];

                  if (imageUrl) {
                    return (
                      <div className="w-32 h-32 md:w-40 md:h-40 shrink-0 bg-muted">
                        <img
                          src={imageUrl}
                          alt={r.title}
                          className="w-full h-full object-cover"
                          loading="lazy"
                          decoding="async"
                          width={160}
                          height={160}
                        />
                      </div>
                    );
                  }

                  if (isLoading) {
                    return (
                      <div className="w-32 h-32 md:w-40 md:h-40 shrink-0 bg-muted overflow-hidden relative">
                        <div className="absolute inset-0 bg-gradient-to-r from-muted via-muted-foreground/10 to-muted animate-shimmer" />
                        <div className="absolute inset-0 flex items-center justify-center">
                          <ChefHat className="w-8 h-8 text-muted-foreground/30" />
                        </div>
                      </div>
                    );
                  }

                  return null;
                })()}

                {/* 우측: 핵심 정보 */}
                <div className="flex-1 p-4 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-bold text-lg leading-tight">{r.title}</h3>
                      <div className="flex items-center gap-1">
                        <ShareButton
                          title={r.title}
                          text={`${r.title} - ${r.time_min}분 레시피`}
                          imageUrl={r.image_url || undefined}
                        />
                        <FavoriteButton
                          key={pendingProcessed?.recipeIndex === idx ? "processed" : "initial"}
                          recommendationId={data.id}
                          recipeIndex={idx}
                          recipeTitle={r.title}
                          recipeImageUrl={r.image_url}
                          likeCount={getLikeCountForRecipe(idx)}
                          onFavoriteChange={(isFav) => handleFavoriteChange(idx, isFav)}
                        />
                        <Badge variant="secondary" className="shrink-0">
                          {idx + 1}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-sm text-muted-foreground mb-3">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {r.time_min}분
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        {r.servings}인분
                      </span>
                      {recipeCompleted > 0 && (
                        <span className="flex items-center gap-1 text-primary">
                          <CircleCheck className="w-3.5 h-3.5" />
                          {recipeCompleted}/{steps.length}
                        </span>
                      )}
                    </div>

                    <div className="space-y-1 text-sm">
                      <div className="flex gap-2">
                        <span className="w-2 h-2 bg-green-500 rounded-full mt-1.5 shrink-0" />
                        <span className="text-muted-foreground">
                          보유: {(r.ingredients_have || []).slice(0, 3).join(", ") || "-"}
                          {(r.ingredients_have || []).length > 3 && ` 외 ${r.ingredients_have.length - 3}개`}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <span className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0" />
                        <span className="text-muted-foreground">
                          추가: {(r.ingredients_need || []).slice(0, 3).join(", ") || "없음"}
                          {(r.ingredients_need || []).length > 3 && ` 외 ${r.ingredients_need.length - 3}개`}
                        </span>
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 w-fit p-0 h-auto text-primary hover:text-primary/80"
                    onClick={() => toggleExpand(idx)}
                    aria-expanded={isExpanded}
                  >
                    {isExpanded ? (
                      <>접기 <ChevronUp className="w-4 h-4 ml-1" /></>
                    ) : (
                      <>상세보기 <ChevronDown className="w-4 h-4 ml-1" /></>
                    )}
                  </Button>
                </div>
              </div>

              {/* 확장 영역 */}
              {isExpanded && (
                <CardContent className="pt-0 pb-6 border-t">
                  <div className="pt-4">
                    <p className="text-muted-foreground mb-4">{r.summary}</p>

                    <div className="grid md:grid-cols-3 gap-4 mb-6">
                      <div className="space-y-2">
                        <h4 className="font-semibold text-sm flex items-center gap-2">
                          <span className="w-2 h-2 bg-primary rounded-full" />
                          총 재료
                        </h4>
                        <div className="text-sm text-muted-foreground">
                          {(r.ingredients_total || []).join(", ") || "-"}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <h4 className="font-semibold text-sm flex items-center gap-2">
                          <span className="w-2 h-2 bg-green-500 rounded-full" />
                          보유 재료
                        </h4>
                        <div className="text-sm text-muted-foreground">
                          {(r.ingredients_have || []).join(", ") || "-"}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <h4 className="font-semibold text-sm flex items-center gap-2">
                          <span className="w-2 h-2 bg-orange-500 rounded-full" />
                          추가 재료
                        </h4>
                        <div className="text-sm text-muted-foreground">
                          {(r.ingredients_need || []).join(", ") || "-"}
                        </div>
                      </div>
                    </div>

                    <Separator className="my-6" />

                    {/* 조리 순서 + 체크리스트 */}
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold flex items-center gap-2">
                          <ChefHat className="w-4 h-4" />
                          조리 순서
                        </h4>
                        {steps.length > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {recipeCompleted}/{steps.length} 완료
                          </span>
                        )}
                      </div>
                      {/* 진행률 바 */}
                      {steps.length > 0 && (
                        <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full transition-all duration-300"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                      )}
                      <ol className="space-y-3">
                        {steps.map((s: string, i: number) => {
                          const isDone = completedSteps[idx]?.has(i) || false;
                          return (
                            <li
                              key={i}
                              className="flex gap-3 cursor-pointer group"
                              onClick={() => toggleStep(idx, i)}
                            >
                              <Badge
                                variant={isDone ? "default" : "outline"}
                                className={`h-6 w-6 flex items-center justify-center p-0 shrink-0 transition-colors ${
                                  isDone ? "bg-primary" : "group-hover:border-primary"
                                }`}
                              >
                                {isDone ? <Check className="w-3 h-3" /> : i + 1}
                              </Badge>
                              <span className={`text-sm leading-6 transition-colors ${isDone ? "line-through text-muted-foreground" : ""}`}>
                                {s}
                              </span>
                            </li>
                          );
                        })}
                      </ol>
                    </div>

                    {r.tips?.length > 0 && (
                      <>
                        <Separator className="my-6" />
                        <div className="space-y-3">
                          <h4 className="font-semibold flex items-center gap-2">
                            <Lightbulb className="w-4 h-4" />
                            조리 팁
                          </h4>
                          <ul className="space-y-2">
                            {r.tips.map((t: string, i: number) => (
                              <li key={i} className="text-sm text-muted-foreground flex gap-2">
                                <span className="text-primary">•</span>
                                {t}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>
          );
        })}
      </div>

      {/* 장보기 리스트 */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-2">
            <ShoppingCart className="w-5 h-5" />
            <h2 className="font-bold text-lg">장보기 리스트</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            3개 레시피에 필요한 추가 재료 모음 (클릭하면 보유 재료에 추가)
          </p>

          {(data.shopping_list || []).length > 0 ? (
            <>
              <ul className="grid md:grid-cols-2 gap-2">
                {data.shopping_list.map((it: ShoppingItem, idx: number) => {
                  const inPantry = isInPantry(it.item);
                  return (
                    <li key={idx} className="flex items-center justify-between text-sm group">
                      <div className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${inPantry ? "bg-green-500" : "bg-primary"}`} />
                        <span className={inPantry ? "line-through text-muted-foreground" : ""}>
                          {it.item}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        {it.purchase_url && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            asChild
                          >
                            <a
                              href={it.purchase_url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <ExternalLink className="w-3 h-3 mr-1" />
                              쿠팡에서 구매
                            </a>
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => addToPantry(it.item)}
                          disabled={inPantry}
                          className={`h-7 px-2 opacity-0 group-hover:opacity-100 transition-opacity ${
                            inPantry ? "opacity-100" : ""
                          }`}
                        >
                          {inPantry ? (
                            <>
                              <Check className="w-3.5 h-3.5 mr-1 text-green-500" />
                              <span className="text-xs text-green-600">추가됨</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3.5 h-3.5 mr-1" />
                              <span className="text-xs">보유재료에 추가</span>
                            </>
                          )}
                        </Button>
                      </div>
                    </li>
                  );
                })}
              </ul>
              {data.shopping_list.some((it: ShoppingItem) => it.purchase_url) && (
                <p className="text-xs text-muted-foreground mt-4">
                  이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">모든 재료를 보유하고 있습니다!</p>
          )}
        </CardContent>
      </Card>

      <AdUnit slot="9592260736" className="my-6" />
    </main>
  );
}
