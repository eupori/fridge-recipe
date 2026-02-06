"use client";

import { useEffect, useState } from "react";
import { getRecommendation } from "../../../lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowLeft, Clock, Users, ChefHat, ShoppingCart, Lightbulb, ChevronDown, ChevronUp } from "lucide-react";
import { FavoriteButton } from "@/components/FavoriteButton";

export default function ResultPage({ params }: { params: { id: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const rec = await getRecommendation(params.id);
        setData(rec);
      } catch (e: any) {
        setError(e?.message ?? "불러오기에 실패했습니다");
      }
    })();
  }, [params.id]);

  const toggleExpand = (idx: number) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  if (error) {
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <div className="p-4 bg-destructive/10 text-destructive rounded-md">{error}</div>
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
      <Button variant="ghost" asChild className="mb-6">
        <a href="/">
          <ArrowLeft className="mr-2 h-4 w-4" />
          다시 입력
        </a>
      </Button>

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
                {r.image_url && (
                  <div className="w-32 h-32 md:w-40 md:h-40 shrink-0 bg-muted">
                    <img
                      src={r.image_url}
                      alt={r.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}

                {/* 우측: 핵심 정보 */}
                <div className="flex-1 p-4 flex flex-col justify-between">
                  <div>
                    {/* 제목 + 번호 + 즐겨찾기 */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-bold text-lg leading-tight">{r.title}</h3>
                      <div className="flex items-center gap-1">
                        <FavoriteButton
                          recommendationId={data.id}
                          recipeIndex={idx}
                          recipeTitle={r.title}
                          recipeImageUrl={r.image_url}
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

      {/* 장보기 리스트 */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 mb-2">
            <ShoppingCart className="w-5 h-5" />
            <h2 className="font-bold text-lg">장보기 리스트</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-4">3개 레시피에 필요한 추가 재료 모음</p>

          {(data.shopping_list || []).length > 0 ? (
            <ul className="grid md:grid-cols-2 gap-2">
              {data.shopping_list.map((it: any, idx: number) => (
                <li key={idx} className="flex items-center gap-2 text-sm">
                  <span className="w-1.5 h-1.5 bg-primary rounded-full" />
                  {it.item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">모든 재료를 보유하고 있습니다!</p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
