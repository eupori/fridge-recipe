import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Clock, Users, Eye, ExternalLink } from "lucide-react";
import { getReferenceRecipe, getReferenceRecipes } from "@/lib/api";
import { Breadcrumb } from "@/components/Breadcrumb";
import { RecipeCTA } from "@/components/RecipeCTA";
import { RecipeCard } from "@/components/RecipeCard";

export const revalidate = 86400;

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) return { title: "레시피를 찾을 수 없습니다 | 냉탐정" };

  const recipe = await getReferenceRecipe(id);
  if (!recipe) return { title: "레시피를 찾을 수 없습니다 | 냉탐정" };

  const description = `${recipe.title} 만드는 법 - ${recipe.key_ingredients.join(", ")}으로 만드는 ${recipe.category} 레시피. ${recipe.time_min ? `조리시간 ${recipe.time_min}분.` : ""}`;
  const url = `https://recipe.eupori.dev/recipes/${recipe.id}`;

  return {
    title: `${recipe.title} 만드는 법 | 냉탐정`,
    description,
    alternates: { canonical: url },
    openGraph: {
      title: `${recipe.title} 만드는 법`,
      description,
      url,
      type: "article",
    },
    twitter: {
      card: "summary",
      title: `${recipe.title} 만드는 법 | 냉탐정`,
      description,
    },
  };
}

export default async function RecipeDetailPage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id, 10);
  if (isNaN(id)) notFound();

  const recipe = await getReferenceRecipe(id);
  if (!recipe) notFound();

  // 같은 카테고리의 관련 레시피 (자기 자신 제외)
  const related = await getReferenceRecipes({ category: recipe.category, per_page: 7 });
  const relatedRecipes = related.items.filter((r) => r.id !== recipe.id).slice(0, 6);

  // JSON-LD: Recipe
  const recipeJsonLd = {
    "@context": "https://schema.org",
    "@type": "Recipe",
    name: recipe.title,
    description: `${recipe.title} - ${recipe.category} 레시피`,
    ...(recipe.time_min ? { totalTime: `PT${recipe.time_min}M`, cookTime: `PT${recipe.time_min}M` } : {}),
    ...(recipe.servings ? { recipeYield: `${recipe.servings}인분` } : {}),
    recipeCategory: recipe.category,
    recipeCuisine: "Korean",
    recipeIngredient: recipe.all_ingredients,
    recipeInstructions: recipe.steps.map((step, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      text: step,
    })),
    author: { "@type": "Organization", name: "냉탐정" },
    ...(recipe.source_url ? { isBasedOn: recipe.source_url } : {}),
    ...(recipe.rating ? { aggregateRating: { "@type": "AggregateRating", ratingValue: recipe.rating, bestRating: 5 } } : {}),
  };

  // JSON-LD: BreadcrumbList
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: "https://recipe.eupori.dev" },
      { "@type": "ListItem", position: 2, name: "레시피", item: "https://recipe.eupori.dev/recipes" },
      { "@type": "ListItem", position: 3, name: recipe.category, item: `https://recipe.eupori.dev/recipes?category=${encodeURIComponent(recipe.category)}` },
      { "@type": "ListItem", position: 4, name: recipe.title },
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(recipeJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <main className="container max-w-3xl mx-auto px-4 py-6 sm:py-8">
        {/* 브레드크럼 */}
        <Breadcrumb
          items={[
            { label: "홈", href: "/" },
            { label: "레시피", href: "/recipes" },
            { label: recipe.category, href: `/recipes?category=${encodeURIComponent(recipe.category)}` },
            { label: recipe.title },
          ]}
        />

        {/* 헤더 */}
        <div className="mb-6">
          <span className="inline-block text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary mb-2">
            {recipe.category}
          </span>
          <h1 className="text-2xl sm:text-3xl font-bold mb-3">{recipe.title}</h1>

          {/* 메타 정보 */}
          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            {recipe.time_min && (
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {recipe.time_min}분
              </span>
            )}
            {recipe.servings && (
              <span className="flex items-center gap-1">
                <Users className="w-4 h-4" />
                {recipe.servings}인분
              </span>
            )}
            {recipe.view_count > 0 && (
              <span className="flex items-center gap-1">
                <Eye className="w-4 h-4" />
                조회 {recipe.view_count.toLocaleString()}
              </span>
            )}
            {recipe.technique && (
              <span className="px-2 py-0.5 rounded bg-muted text-xs">{recipe.technique}</span>
            )}
          </div>
        </div>

        {/* 재료 */}
        <section className="mb-8">
          <h2 className="text-lg font-bold mb-3">재료</h2>
          <div className="border rounded-xl p-4 bg-card">
            <div className="grid grid-cols-2 gap-2">
              {recipe.all_ingredients.map((ing, i) => (
                <div key={i} className="flex items-center gap-2 text-sm py-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0" />
                  {ing}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 조리 순서 */}
        <section className="mb-8">
          <h2 className="text-lg font-bold mb-3">조리 순서</h2>
          <div className="space-y-4">
            {recipe.steps.map((step, i) => (
              <div key={i} className="flex gap-3">
                <span className="flex items-center justify-center w-7 h-7 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0 mt-0.5">
                  {i + 1}
                </span>
                <p className="text-sm leading-relaxed pt-1">{step}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 출처 */}
        <section className="mb-4">
          <div className="text-sm text-muted-foreground border-t pt-4 flex items-center gap-2">
            <span>출처: {recipe.source}</span>
            {recipe.source_url && (
              <a
                href={recipe.source_url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                원본 보기
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </section>

        {/* CTA */}
        <RecipeCTA ingredients={recipe.key_ingredients} />

        {/* 관련 레시피 */}
        {relatedRecipes.length > 0 && (
          <section className="mt-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold">관련 {recipe.category} 레시피</h2>
              <Link
                href={`/recipes?category=${encodeURIComponent(recipe.category)}`}
                className="text-sm text-primary hover:underline"
              >
                더 보기
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {relatedRecipes.map((r) => (
                <RecipeCard
                  key={r.id}
                  id={r.id}
                  title={r.title}
                  category={r.category}
                  keyIngredients={r.key_ingredients}
                  timeMin={r.time_min}
                  servings={r.servings}
                  viewCount={r.view_count}
                />
              ))}
            </div>
          </section>
        )}
      </main>
    </>
  );
}
