import type { Metadata } from "next";
import { resolveImageUrl } from "@/lib/api";
import ResultClient from "./ResultClient";

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const res = await fetch(`${API_BASE}/recommendations/${params.id}`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error();
    const data = await res.json();

    const titles = data.recipes?.map((r: { title: string }) => r.title).join(", ") ?? "";
    const firstImage = resolveImageUrl(data.recipes?.[0]?.image_url);

    const description = `오머먹 - 냉장고 재료로 만드는 15분 레시피: ${titles}`;
    const url = `https://eupori.dev/r/${params.id}`;

    return {
      title: `${titles} | 오머먹`,
      description,
      alternates: { canonical: url },
      openGraph: {
        title: titles,
        description,
        url,
        ...(firstImage ? { images: [firstImage] } : {}),
      },
      twitter: {
        card: firstImage ? "summary_large_image" : "summary",
        title: `${titles} | 오머먹`,
        description,
        ...(firstImage ? { images: [firstImage] } : {}),
      },
    };
  } catch {
    return {
      title: "추천 레시피 | 오머먹",
      description: "오머먹 - AI가 추천한 냉장고 파먹기 레시피",
    };
  }
}

async function getRecipeData(id: string) {
  try {
    const res = await fetch(`${API_BASE}/recommendations/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export default async function ResultPage({ params }: { params: { id: string } }) {
  const data = await getRecipeData(params.id);

  // JSON-LD 구조화 데이터
  const jsonLd = data?.recipes?.map((r: { title: string; summary?: string; time_min?: number; servings?: number; image_url?: string | null; ingredients_total?: string[]; steps?: string[] }) => ({
    "@context": "https://schema.org",
    "@type": "Recipe",
    name: r.title,
    description: r.summary || `${r.title} - 오머먹 AI 추천 레시피`,
    ...(r.time_min ? { totalTime: `PT${r.time_min}M` } : {}),
    ...(r.servings ? { recipeYield: `${r.servings}인분` } : {}),
    ...(r.image_url ? { image: resolveImageUrl(r.image_url) } : {}),
    recipeIngredient: r.ingredients_total || [],
    recipeInstructions: (r.steps || []).map((step: string, i: number) => ({
      "@type": "HowToStep",
      position: i + 1,
      text: step,
    })),
    author: { "@type": "Organization", name: "오머먹" },
  })) || [];

  return (
    <>
      {jsonLd.map((ld: object, i: number) => (
        <script
          key={i}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
        />
      ))}
      <ResultClient id={params.id} />
    </>
  );
}
