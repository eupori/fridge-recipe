"use client";

import { useRouter, useSearchParams } from "next/navigation";

const CATEGORIES = [
  { value: "", label: "전체" },
  { value: "밥", label: "밥" },
  { value: "국물", label: "국물" },
  { value: "반찬단품", label: "반찬" },
  { value: "면분식", label: "면/분식" },
  { value: "양식", label: "양식" },
  { value: "아시안", label: "아시안" },
  { value: "퓨전", label: "퓨전" },
  { value: "안주", label: "안주" },
  { value: "간식", label: "간식" },
];

export function CategoryTabs({ current }: { current: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleClick = (category: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (category) {
      params.set("category", category);
    } else {
      params.delete("category");
    }
    params.delete("page");
    router.push(`/recipes?${params.toString()}`);
  };

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      {CATEGORIES.map((cat) => (
        <button
          key={cat.value}
          onClick={() => handleClick(cat.value)}
          className={`shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            current === cat.value
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          {cat.label}
        </button>
      ))}
    </div>
  );
}
