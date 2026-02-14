"use client";

import { useEffect, useState } from "react";
import { getRecommendation, addFavorite, getRecipeLikeStats, getRecipeImages, RecommendationLikeStats } from "../../../lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Clock, Users, ChefHat, ShoppingCart, Lightbulb, ChevronDown, ChevronUp, Plus, Check, ExternalLink } from "lucide-react";
import { FavoriteButton } from "@/components/FavoriteButton";
import AdUnit from "@/components/AdUnit";
import { useAuth } from "@/lib/auth-context";

const PANTRY_STORAGE_KEY = "pantry-items";

export default function ResultPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [likeStats, setLikeStats] = useState<RecommendationLikeStats | null>(null);
  const [pantryItems, setPantryItems] = useState<string[]>([]);
  const [recipeImages, setRecipeImages] = useState<(string | null)[]>([]);
  const [imageLoading, setImageLoading] = useState<boolean[]>([]);
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
        // 추천 데이터와 좋아요 통계를 병렬로 로드
        const [rec, stats] = await Promise.all([
          getRecommendation(params.id),
          getRecipeLikeStats(params.id),
        ]);
        setData(rec);
        setLikeStats(stats);
      } catch (e: any) {
        setError(e?.message ?? "불러오기에 실패했습니다");
      }
    })();
  }, [params.id]);

  // 이미지가 없는 레시피에 대해 비동기로 이미지 로드 (배치 요청)
  useEffect(() => {
    if (!data?.recipes) return;

    const recipes = data.recipes as any[];
    // 초기 이미지 상태 설정 (기존 image_url 사용)
    setRecipeImages(recipes.map((r: any) => r.image_url ?? null));

    // 이미지가 없는 레시피 찾기
    const missingRecipes = recipes
      .map((r: any, i: number) => (!r.image_url ? { index: i, title: r.title } : null))
      .filter((x): x is { index: number; title: string } => x !== null);

    if (missingRecipes.length === 0) return;

    // 로딩 상태 설정
    const missingSet = new Set(missingRecipes.map((m) => m.index));
    setImageLoading(recipes.map((_, i) => missingSet.has(i)));

    // 1개 배치 요청으로 모든 이미지 생성 (recommendation_id 전달하여 DB 업데이트)
    (async () => {
      const titles = missingRecipes.map((m) => m.title);
      const results = await getRecipeImages(titles, data.id);

      // 결과를 제목 기준으로 매핑
      const imageMap = new Map(results.map((r) => [r.title, r.image_url]));

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
  // 별도의 state로 처리 완료 여부 추적하여 FavoriteButton과 동기화
  const [pendingProcessed, setPendingProcessed] = useState<{recipeIndex: number} | null>(null);

  useEffect(() => {
    const processPendingFavorite = async () => {
      if (!user) return;

      const pendingStr = localStorage.getItem("pendingFavorite");
      if (!pendingStr) return;

      try {
        const pending = JSON.parse(pendingStr);

        // 10분 타임아웃 체크
        if (Date.now() - pending.timestamp > 10 * 60 * 1000) {
          localStorage.removeItem("pendingFavorite");
          return;
        }

        // 현재 페이지의 추천 ID와 일치하면 자동 즐겨찾기
        if (pending.recommendationId === params.id) {
          try {
            await addFavorite(
              pending.recommendationId,
              pending.recipeIndex,
              pending.recipeTitle,
              pending.recipeImageUrl
            );
            // 성공 시 좋아요 수 업데이트
            handleFavoriteChange(pending.recipeIndex, true);
            setPendingProcessed({ recipeIndex: pending.recipeIndex });
          } catch (err: any) {
            // 이미 즐겨찾기된 경우 무시 (중복 에러)
            if (err.message?.includes("이미 즐겨찾기")) {
              setPendingProcessed({ recipeIndex: pending.recipeIndex });
            }
          }
          localStorage.removeItem("pendingFavorite");
        }
      } catch (e) {
        // 파싱 실패 시 pendingFavorite 삭제
        localStorage.removeItem("pendingFavorite");
      }
    };

    processPendingFavorite();
  }, [user, params.id]);

  const toggleExpand = (idx: number) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
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
        <p className="text-muted-foreground text-sm">ID: {data.id}</p>
      </div>

      <div className="space-y-4 mb-8">
        {data.recipes?.map((r: any, idx: number) => {
          const isExpanded = expandedIdx === idx;

          return (
            <Card key={idx} className="overflow-hidden">
              {/* 메인 영역: 이미지 + 핵심 정보 (가로 배치) */}
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
                    {/* 제목 + 번호 + 즐겨찾기 */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-bold text-lg leading-tight">{r.title}</h3>
                      <div className="flex items-center gap-1">
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

                    {/* 시간, 인분 */}
                    <div className="flex items-center gap-3 text-sm text-muted-foreground mb-3">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {r.time_min}분
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        {r.servings}인분
                      </span>
                    </div>

                    {/* 재료 요약 */}
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

                  {/* 상세보기 버튼 */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-2 w-fit p-0 h-auto text-primary hover:text-primary/80"
                    onClick={() => toggleExpand(idx)}
                  >
                    {isExpanded ? (
                      <>접기 <ChevronUp className="w-4 h-4 ml-1" /></>
                    ) : (
                      <>상세보기 <ChevronDown className="w-4 h-4 ml-1" /></>
                    )}
                  </Button>
                </div>
              </div>

              {/* 확장 영역: 상세 정보 */}
              {isExpanded && (
                <CardContent className="pt-0 pb-6 border-t">
                  <div className="pt-4">
                    {/* 요약 */}
                    <p className="text-muted-foreground mb-4">{r.summary}</p>

                    {/* 전체 재료 */}
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

                    {/* 조리 순서 */}
                    <div className="space-y-3">
                      <h4 className="font-semibold flex items-center gap-2">
                        <ChefHat className="w-4 h-4" />
                        조리 순서
                      </h4>
                      <ol className="space-y-3">
                        {(r.steps || []).map((s: string, i: number) => (
                          <li key={i} className="flex gap-3">
                            <Badge variant="outline" className="h-6 w-6 flex items-center justify-center p-0 shrink-0">
                              {i + 1}
                            </Badge>
                            <span className="text-sm leading-6">{s}</span>
                          </li>
                        ))}
                      </ol>
                    </div>

                    {/* 조리 팁 */}
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

      <AdUnit slot="1234567890" className="my-6" />

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
                {data.shopping_list.map((it: any, idx: number) => {
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
              {data.shopping_list.some((it: any) => it.purchase_url) && (
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

      <AdUnit slot="1234567890" className="my-6" />
    </main>
  );
}
