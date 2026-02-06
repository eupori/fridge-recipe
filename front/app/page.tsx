"use client";

import { useMemo, useState } from "react";
import { createRecommendation } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChefHat, Clock, Users, Utensils } from "lucide-react";

export default function HomePage() {
  const [ingredientsText, setIngredientsText] = useState("계란, 김치, 양파");
  const [excludeText, setExcludeText] = useState("");
  const [timeLimit, setTimeLimit] = useState(15);
  const [servings, setServings] = useState(1);
  const [tools, setTools] = useState<string[]>(["프라이팬"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
            <Label htmlFor="ingredients">재료</Label>
            <Textarea
              id="ingredients"
              value={ingredientsText}
              onChange={(e) => setIngredientsText(e.target.value)}
              rows={5}
              placeholder="예: 계란, 김치, 양파&#10;두부"
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
              <Select value={timeLimit.toString()} onValueChange={(v) => setTimeLimit(Number(v))}>
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
              <Select value={servings.toString()} onValueChange={(v) => setServings(Number(v))}>
                <SelectTrigger id="servings">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1인분</SelectItem>
                  <SelectItem value="2">2인분</SelectItem>
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
            {loading ? "생성 중…" : "레시피 3개 추천받기"}
          </Button>

          <p className="text-xs text-center text-muted-foreground">
            MVP: 지금은 백엔드가 더미 응답을 반환하도록 되어 있어요. LLM 연동은 다음 단계에서 붙입니다.
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
