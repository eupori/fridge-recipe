"use client";

import { useState, useEffect, useRef } from "react";
import { ChefHat, Lightbulb } from "lucide-react";

const STAGES = [
  { until: 3, message: "YouTube에서 인기 레시피 검색 중...", progress: 15 },
  { until: 6, message: "인기 영상에서 레시피 정보 분석 중...", progress: 35 },
  { until: 10, message: "맞춤 레시피 구성 중...", progress: 55 },
  { until: 15, message: "레시피 이미지 생성 중...", progress: 75 },
  { until: Infinity, message: "거의 다 됐어요! 마무리 중...", progress: 90 },
];

const COOKING_TIPS = [
  "김치는 잘 익은 것이 볶음밥에 더 맛있어요",
  "계란은 실온에 꺼내두면 더 잘 풀려요",
  "파스타 삶을 때 소금을 넉넉히 넣으세요",
  "고기는 키친타올로 물기를 제거하면 잘 구워져요",
  "마늘은 너무 센 불에 볶으면 쓴맛이 나요",
  "양파를 먼저 볶으면 단맛이 살아나요",
  "된장찌개는 들기름 한 방울이 맛의 비결",
  "라면 물은 550ml가 황금비율이에요",
  "볶음밥은 찬밥으로 해야 파라파라해요",
  "두부는 키친타올로 물기를 빼면 잘 부서지지 않아요",
  "고추장은 불에 살짝 볶으면 감칠맛이 올라가요",
  "참기름은 불을 끄고 마지막에 넣으세요",
  "국물 요리는 센 불로 끓이다 약불로 줄이세요",
  "채소는 큰 것부터 먼저 볶으세요",
  "간장은 조금씩 넣고 맛을 보며 조절하세요",
  "감자는 찬물부터 삶아야 고르게 익어요",
  "생선은 껍질부터 구우면 모양이 예뻐요",
  "카레는 하루 지나면 더 맛있어요",
];

function getRandomTip(exclude: number): number {
  let next: number;
  do {
    next = Math.floor(Math.random() * COOKING_TIPS.length);
  } while (next === exclude && COOKING_TIPS.length > 1);
  return next;
}

export default function RecipeLoadingOverlay({ loading }: { loading: boolean }) {
  const [elapsed, setElapsed] = useState(0);
  const [tipIndex, setTipIndex] = useState(() => Math.floor(Math.random() * COOKING_TIPS.length));
  const [tipFading, setTipFading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tipIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Elapsed timer
  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      return;
    }
    setElapsed(0);
    intervalRef.current = setInterval(() => {
      setElapsed((prev) => prev + 0.5);
    }, 500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loading]);

  // Tip rotation with fade
  useEffect(() => {
    if (!loading) return;
    setTipIndex(Math.floor(Math.random() * COOKING_TIPS.length));
    tipIntervalRef.current = setInterval(() => {
      setTipFading(true);
      setTimeout(() => {
        setTipIndex((prev) => getRandomTip(prev));
        setTipFading(false);
      }, 300);
    }, 5000);
    return () => {
      if (tipIntervalRef.current) clearInterval(tipIntervalRef.current);
      setTipFading(false);
    };
  }, [loading]);

  if (!loading) return null;

  const stage = STAGES.find((s) => elapsed < s.until) ?? STAGES[STAGES.length - 1];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm" role="alert" aria-live="assertive">
      <div className="flex flex-col items-center gap-6 px-6 w-full max-w-sm text-center">
        {/* Animated icon */}
        <ChefHat className="w-14 h-14 text-primary animate-bounce" />

        {/* Stage message */}
        <p className="text-lg font-medium text-foreground">{stage.message}</p>

        {/* Progress bar */}
        <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-1000 ease-out"
            style={{ width: `${stage.progress}%` }}
          />
        </div>

        {/* Cooking tip */}
        <div
          className={`flex items-start gap-2 text-sm text-muted-foreground transition-opacity duration-300 ${
            tipFading ? "opacity-0" : "opacity-100"
          }`}
        >
          <Lightbulb className="w-4 h-4 mt-0.5 shrink-0 text-yellow-500" />
          <span>{COOKING_TIPS[tipIndex]}</span>
        </div>
      </div>
    </div>
  );
}
