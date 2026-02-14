"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ChefHat, Sparkles, Heart } from "lucide-react";

const STORAGE_KEY = "onboarding-done";

const steps = [
  {
    icon: ChefHat,
    title: "재료를 입력하세요",
    description: "냉장고에 있는 재료를 쉼표로 구분해서 입력해주세요. 보유 재료를 미리 등록해두면 더 편리해요.",
  },
  {
    icon: Sparkles,
    title: "AI가 레시피를 추천해요",
    description: "입력한 재료를 기반으로 15분 안에 만들 수 있는 레시피 3개와 장보기 리스트를 만들어드려요.",
  },
  {
    icon: Heart,
    title: "즐겨찾기로 저장하세요",
    description: "마음에 드는 레시피는 하트를 눌러 즐겨찾기에 저장하고 언제든 다시 볼 수 있어요.",
  },
];

export function Onboarding() {
  const [show, setShow] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setShow(true);
      }
    } catch {
      // SSR or storage unavailable
    }
  }, []);

  const close = () => {
    setShow(false);
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignore
    }
  };

  const next = () => {
    if (step < steps.length - 1) {
      setStep(step + 1);
    } else {
      close();
    }
  };

  if (!show) return null;

  const current = steps[step];
  const Icon = current.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-card rounded-2xl shadow-2xl max-w-sm w-full p-6 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
          <Icon className="w-8 h-8 text-primary" />
        </div>

        <h2 className="text-xl font-bold mb-2">{current.title}</h2>
        <p className="text-muted-foreground text-sm mb-6 leading-relaxed">{current.description}</p>

        {/* 진행 표시 */}
        <div className="flex justify-center gap-2 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === step ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>

        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={close} className="flex-1">
            건너뛰기
          </Button>
          <Button onClick={next} className="flex-1">
            {step < steps.length - 1 ? "다음" : "시작하기"}
          </Button>
        </div>
      </div>
    </div>
  );
}
