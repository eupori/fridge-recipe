"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  getMealPlans,
  getMealPlan,
  createMealPlan,
  deleteMealPlan,
  addMealSlot,
  removeMealSlot,
  getMealPlanShoppingList,
  getFavorites,
  getSearchHistories,
  resolveImageUrl,
} from "@/lib/api";
import type {
  FavoriteResponse,
  SearchHistoryResponse,
  MealPlanListItem,
  MealPlanResponse,
  MealSlotResponse,
} from "@/lib/api";
import type { ShoppingItem } from "@/types/recommendation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Calendar,
  Plus,
  Trash2,
  ShoppingCart,
  X,
  ExternalLink,
  Heart,
  History,
} from "lucide-react";
import AdUnit from "@/components/AdUnit";
import Link from "next/link";

const DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"];
const MEAL_TYPES = ["breakfast", "lunch", "dinner"] as const;
const MEAL_LABELS: Record<string, string> = {
  breakfast: "아침",
  lunch: "점심",
  dinner: "저녁",
};
const COUPANG_STYLE = {
  purchaseClass: "bg-[#E44232] text-white hover:bg-[#E44232]/90 border-transparent",
};

function getThisMonday(): string {
  const d = new Date();
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  return monday.toISOString().slice(0, 10);
}

export default function MealPlannerPage() {
  const { user, loading: authLoading } = useAuth();
  const [plans, setPlans] = useState<MealPlanListItem[]>([]);
  const [activePlan, setActivePlan] = useState<MealPlanResponse | null>(null);
  const [shoppingList, setShoppingList] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);

  // 레시피 선택 패널
  const [selectingSlot, setSelectingSlot] = useState<{
    day: number;
    meal: string;
  } | null>(null);
  const [selectTab, setSelectTab] = useState<"favorites" | "history">("favorites");
  const [favorites, setFavorites] = useState<FavoriteResponse[]>([]);
  const [histories, setHistories] = useState<SearchHistoryResponse[]>([]);

  // 새 식단 생성
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const loadPlans = useCallback(async () => {
    try {
      const data = await getMealPlans();
      setPlans(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  const loadPlanDetail = useCallback(async (planId: string) => {
    const plan = await getMealPlan(planId);
    if (plan) {
      setActivePlan(plan);
      const sl = await getMealPlanShoppingList(planId);
      setShoppingList(sl);
    }
  }, []);

  useEffect(() => {
    if (user) loadPlans();
    else setLoading(false);
  }, [user, loadPlans]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    try {
      const plan = await createMealPlan(newTitle.trim(), getThisMonday());
      setShowCreate(false);
      setNewTitle("");
      await loadPlans();
      await loadPlanDetail(plan.id);
    } catch {
      // ignore
    }
  };

  const handleDelete = async (planId: string) => {
    try {
      await deleteMealPlan(planId);
      if (activePlan?.id === planId) {
        setActivePlan(null);
        setShoppingList([]);
      }
      await loadPlans();
    } catch {
      // ignore
    }
  };

  const openSlotSelector = async (day: number, meal: string) => {
    setSelectingSlot({ day, meal });
    setSelectTab("favorites");
    try {
      const [favs, hist] = await Promise.all([
        getFavorites(),
        getSearchHistories(20),
      ]);
      setFavorites(favs);
      setHistories(hist);
    } catch {
      // ignore
    }
  };

  const handleSelectRecipe = async (
    recommendationId: string,
    recipeIndex: number,
    recipeTitle: string,
    recipeImageUrl: string | null
  ) => {
    if (!activePlan || !selectingSlot) return;
    try {
      await addMealSlot(
        activePlan.id,
        selectingSlot.day,
        selectingSlot.meal,
        recommendationId,
        recipeIndex,
        recipeTitle,
        recipeImageUrl
      );
      setSelectingSlot(null);
      await loadPlanDetail(activePlan.id);
    } catch {
      // ignore
    }
  };

  const handleRemoveSlot = async (slotId: string) => {
    if (!activePlan) return;
    try {
      await removeMealSlot(activePlan.id, slotId);
      await loadPlanDetail(activePlan.id);
    } catch {
      // ignore
    }
  };

  const getSlot = (day: number, meal: string): MealSlotResponse | undefined => {
    return activePlan?.slots.find(
      (s) => s.day_of_week === day && s.meal_type === meal
    );
  };

  // 로그인 체크
  if (!authLoading && !user) {
    return (
      <main className="container max-w-4xl mx-auto py-10 px-4">
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-xl font-bold mb-2">로그인이 필요합니다</h2>
            <p className="text-muted-foreground mb-6">
              식단 플래너는 로그인 후 이용할 수 있습니다.
            </p>
            <Button asChild>
              <Link href="/login">로그인</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    );
  }

  if (loading || authLoading) {
    return (
      <main className="container max-w-4xl mx-auto py-10 px-4">
        <p className="text-muted-foreground">불러오는 중...</p>
      </main>
    );
  }

  return (
    <main className="container max-w-4xl mx-auto py-10 px-4">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Calendar className="w-6 h-6" />
          <h1 className="text-2xl font-bold">주간 식단 플래너</h1>
        </div>
        {!activePlan && (
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-1" />
            새 식단
          </Button>
        )}
        {activePlan && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setActivePlan(null);
              setShoppingList([]);
            }}
          >
            목록으로
          </Button>
        )}
      </div>

      {/* 새 식단 생성 폼 */}
      {showCreate && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="식단 이름 (예: 3월 1주차)"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                className="flex-1 px-3 py-2 border rounded-md bg-background text-sm"
                maxLength={100}
                autoFocus
              />
              <Button size="sm" onClick={handleCreate} disabled={!newTitle.trim()}>
                생성
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowCreate(false);
                  setNewTitle("");
                }}
              >
                취소
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 식단 목록 */}
      {!activePlan && (
        <div className="space-y-3">
          {plans.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Calendar className="w-10 h-10 mx-auto mb-3 text-muted-foreground" />
                <p className="text-muted-foreground mb-4">
                  아직 식단이 없습니다. 새 식단을 만들어보세요!
                </p>
                <Button size="sm" onClick={() => setShowCreate(true)}>
                  <Plus className="w-4 h-4 mr-1" />
                  첫 식단 만들기
                </Button>
              </CardContent>
            </Card>
          ) : (
            plans.map((p) => (
              <Card
                key={p.id}
                className="cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => loadPlanDetail(p.id)}
              >
                <CardContent className="py-4 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{p.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {p.week_start} 주차 · {p.slot_count}개 레시피
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(p.id);
                    }}
                  >
                    <Trash2 className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {/* 주간 그리드 */}
      {activePlan && (
        <>
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold">{activePlan.title}</h2>
                <Badge variant="secondary">{activePlan.week_start} 주차</Badge>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      <th className="p-2 text-sm font-medium text-muted-foreground w-12" />
                      {DAY_LABELS.map((d, i) => (
                        <th
                          key={i}
                          className="p-2 text-sm font-medium text-center min-w-[5rem]"
                        >
                          {d}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {MEAL_TYPES.map((meal) => (
                      <tr key={meal}>
                        <td className="p-2 text-sm font-medium text-muted-foreground whitespace-nowrap">
                          {MEAL_LABELS[meal]}
                        </td>
                        {DAY_LABELS.map((_, dayIdx) => {
                          const slot = getSlot(dayIdx, meal);
                          return (
                            <td key={dayIdx} className="p-1">
                              {slot ? (
                                <div className="relative group bg-muted/50 rounded-lg p-1.5 text-center min-h-[4rem] flex flex-col items-center justify-center">
                                  {slot.recipe_image_url && (
                                    <img
                                      src={resolveImageUrl(slot.recipe_image_url) || ""}
                                      alt={slot.recipe_title}
                                      className="w-10 h-10 rounded object-cover mb-1"
                                    />
                                  )}
                                  <span className="text-xs leading-tight line-clamp-2">
                                    {slot.recipe_title}
                                  </span>
                                  <button
                                    onClick={() => handleRemoveSlot(slot.id)}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                  >
                                    <X className="w-3 h-3" />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => openSlotSelector(dayIdx, meal)}
                                  className="w-full min-h-[4rem] rounded-lg border-2 border-dashed border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/30 transition-colors flex items-center justify-center"
                                >
                                  <Plus className="w-4 h-4 text-muted-foreground/40" />
                                </button>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* 레시피 선택 패널 */}
          {selectingSlot && (
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">
                    {DAY_LABELS[selectingSlot.day]} {MEAL_LABELS[selectingSlot.meal]} 레시피 선택
                  </h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectingSlot(null)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                {/* 탭 */}
                <div className="flex gap-2 mb-4">
                  <Button
                    variant={selectTab === "favorites" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectTab("favorites")}
                  >
                    <Heart className="w-4 h-4 mr-1" />
                    즐겨찾기
                  </Button>
                  <Button
                    variant={selectTab === "history" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectTab("history")}
                  >
                    <History className="w-4 h-4 mr-1" />
                    최근 검색
                  </Button>
                </div>

                {/* 즐겨찾기 탭 */}
                {selectTab === "favorites" && (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {favorites.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        즐겨찾기한 레시피가 없습니다.
                      </p>
                    ) : (
                      favorites.map((fav) => (
                        <div
                          key={fav.id}
                          className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            {fav.recipe_image_url && (
                              <img
                                src={resolveImageUrl(fav.recipe_image_url) || ""}
                                alt={fav.recipe_title}
                                className="w-8 h-8 rounded object-cover shrink-0"
                              />
                            )}
                            <span className="text-sm truncate">{fav.recipe_title}</span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              handleSelectRecipe(
                                fav.recommendation_id,
                                fav.recipe_index,
                                fav.recipe_title,
                                fav.recipe_image_url
                              )
                            }
                          >
                            선택
                          </Button>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* 최근 검색 탭 */}
                {selectTab === "history" && (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {histories.length === 0 ? (
                      <p className="text-sm text-muted-foreground py-4 text-center">
                        최근 검색 기록이 없습니다.
                      </p>
                    ) : (
                      histories.flatMap((h) =>
                        h.recipe_titles.map((title, rIdx) => (
                          <div
                            key={`${h.id}-${rIdx}`}
                            className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50"
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              {h.recipe_images?.[rIdx] && (
                                <img
                                  src={resolveImageUrl(h.recipe_images[rIdx]) || ""}
                                  alt={title}
                                  className="w-8 h-8 rounded object-cover shrink-0"
                                />
                              )}
                              <span className="text-sm truncate">{title}</span>
                            </div>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() =>
                                handleSelectRecipe(
                                  h.recommendation_id,
                                  rIdx,
                                  title,
                                  h.recipe_images?.[rIdx] ?? null
                                )
                              }
                            >
                              선택
                            </Button>
                          </div>
                        ))
                      )
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 장보기 리스트 */}
          {shoppingList.length > 0 && (
            <Card className="bg-muted/50 mb-6">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <ShoppingCart className="w-5 h-5" />
                  <h2 className="font-bold text-lg">주간 장보기 리스트</h2>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {shoppingList.map((it, idx) => {
                    const purchaseUrl =
                      it.purchase_url ||
                      `https://www.coupang.com/np/search?q=${encodeURIComponent(it.item)}`;
                    return (
                      <div
                        key={idx}
                        className="flex items-center justify-between bg-background rounded-lg py-2 px-3 gap-2"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-orange-400" />
                          <span className="text-sm truncate">{it.item}</span>
                        </div>
                        <a
                          href={purchaseUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md border whitespace-nowrap transition-colors font-medium ${COUPANG_STYLE.purchaseClass}`}
                        >
                          쿠팡
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    );
                  })}
                </div>
                {shoppingList.some((it) => it.purchase_url) && (
                  <p className="text-xs text-muted-foreground mt-3">
                    이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          <AdUnit slot="7845903215" className="my-6" />
        </>
      )}
    </main>
  );
}
