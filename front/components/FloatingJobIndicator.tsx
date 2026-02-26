"use client";

import { useRouter, usePathname } from "next/navigation";
import { useRecipeJob } from "@/lib/recipe-job-context";
import { ChefHat } from "lucide-react";

export default function FloatingJobIndicator() {
  const { isProcessing, progress } = useRecipeJob();
  const pathname = usePathname();
  const router = useRouter();

  // 홈에서는 오버레이가 있으므로 표시하지 않음
  if (!isProcessing || pathname === "/") return null;

  return (
    <button
      onClick={() => router.push("/")}
      className="fixed bottom-20 sm:bottom-6 left-4 right-4 sm:left-auto sm:right-6 sm:w-72 z-40 animate-in slide-in-from-bottom-4 fade-in duration-300"
    >
      <div className="bg-card border shadow-lg rounded-lg p-3 flex items-center gap-3">
        <ChefHat className="w-5 h-5 text-primary shrink-0 animate-bounce" />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-left">레시피 생성 중... {progress}%</p>
          <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden mt-1">
            <div
              className="h-full bg-primary rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${Math.max(progress, 5)}%` }}
            />
          </div>
        </div>
      </div>
    </button>
  );
}
