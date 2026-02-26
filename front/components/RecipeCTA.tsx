import Link from "next/link";
import { ChefHat } from "lucide-react";

export function RecipeCTA({ ingredients }: { ingredients?: string[] }) {
  const query = ingredients?.slice(0, 5).join(",") ?? "";
  const href = query ? `/?ingredients=${encodeURIComponent(query)}` : "/";

  return (
    <div className="border rounded-xl p-6 bg-gradient-to-r from-primary/5 to-primary/10 mt-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex-1">
          <h3 className="font-bold text-lg mb-1">이 재료로 나만의 레시피 만들기</h3>
          <p className="text-sm text-muted-foreground">
            AI가 당신의 냉장고 재료에 맞는 맞춤 레시피 3개를 추천해드립니다.
          </p>
        </div>
        <Link
          href={href}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:bg-primary/90 transition-colors shrink-0"
        >
          <ChefHat className="w-4 h-4" />
          레시피 추천받기
        </Link>
      </div>
    </div>
  );
}
