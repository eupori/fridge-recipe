"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChefHat } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function RecipeReadyToast() {
  const [toast, setToast] = useState<{ id: string } | null>(null);
  const router = useRouter();

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (!window.location.pathname.startsWith("/r/")) {
        setToast({ id: detail.id });
      }
    };
    window.addEventListener("recipe-ready", handler);
    return () => window.removeEventListener("recipe-ready", handler);
  }, []);

  // 5초 자동 닫힘
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(timer);
  }, [toast]);

  if (!toast) return null;

  return (
    <div className="fixed bottom-20 sm:bottom-6 left-4 right-4 sm:left-auto sm:right-6 sm:w-80 z-50 animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="bg-card border shadow-lg rounded-lg p-4 flex items-center gap-3">
        <ChefHat className="w-6 h-6 text-primary shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">레시피가 완성됐어요!</p>
          <p className="text-xs text-muted-foreground">터치하면 바로 확인할 수 있어요</p>
        </div>
        <Button
          size="sm"
          onClick={() => {
            setToast(null);
            router.push(`/r/${toast.id}`);
          }}
        >
          보기
        </Button>
      </div>
    </div>
  );
}
