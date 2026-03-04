import type { Metadata } from "next";
import { Suspense } from "react";
import { getReferenceRecipes, getReferenceRecipeCategories } from "@/lib/api";
import { RecipeCard } from "@/components/RecipeCard";
import { CategoryTabs } from "@/components/CategoryTabs";
import { Pagination } from "@/components/Pagination";

export const revalidate = 86400;

export const metadata: Metadata = {
  title: "한국 레시피 모음 | 냉탐정",
  description: "1,800개 이상의 한국 가정식 레시피를 찾아보세요. 밥, 국물, 반찬, 면/분식 등 카테고리별로 쉽고 빠른 요리법을 확인하세요.",
  alternates: { canonical: "https://recipe.eupori.dev/recipes" },
};

async function RecipeList({ category, page }: { category: string; page: number }) {
  const [data, categories] = await Promise.all([
    getReferenceRecipes({ category: category || undefined, page, per_page: 24 }),
    getReferenceRecipeCategories(),
  ]);

  const totalCount = categories.reduce((sum, c) => sum + c.count, 0);

  return (
    <>
      {/* 헤더 */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold mb-2">레시피 모음</h1>
        <p className="text-muted-foreground text-sm">
          {totalCount.toLocaleString()}개의 검증된 한국 가정식 레시피
        </p>
      </div>

      {/* 카테고리 탭 */}
      <Suspense fallback={null}>
        <CategoryTabs current={category} />
      </Suspense>

      {/* 결과 개수 */}
      <p className="text-sm text-muted-foreground mt-4 mb-4">
        {data.total.toLocaleString()}개의 레시피
      </p>

      {/* 카드 그리드 */}
      {data.items.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
          {data.items.map((recipe) => (
            <RecipeCard
              key={recipe.id}
              id={recipe.id}
              title={recipe.title}
              category={recipe.category}
              keyIngredients={recipe.key_ingredients}
              timeMin={recipe.time_min}
              servings={recipe.servings}
              viewCount={recipe.view_count}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          해당 카테고리에 레시피가 없습니다.
        </div>
      )}

      {/* 페이지네이션 */}
      <Suspense fallback={null}>
        <Pagination currentPage={data.page} totalPages={data.total_pages} />
      </Suspense>
    </>
  );
}

export default async function RecipesPage({
  searchParams,
}: {
  searchParams: { category?: string; page?: string };
}) {
  const category = searchParams.category ?? "";
  const page = Math.max(1, parseInt(searchParams.page ?? "1", 10) || 1);

  return (
    <main className="container max-w-4xl mx-auto px-4 py-6 sm:py-8">
      <Suspense fallback={<div className="text-center py-12 text-muted-foreground">레시피를 불러오는 중...</div>}>
        <RecipeList category={category} page={page} />
      </Suspense>
    </main>
  );
}
