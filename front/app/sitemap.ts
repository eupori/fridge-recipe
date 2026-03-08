import type { MetadataRoute } from "next";

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;
const RECIPES_PER_SITEMAP = 500;

// 사이트맵 인덱스 생성: /sitemap/0.xml, /sitemap/1.xml, ...
export async function generateSitemaps() {
  try {
    const res = await fetch(`${API_BASE}/reference-recipes/sitemap`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [{ id: 0 }];

    const entries: { id: number }[] = await res.json();
    const count = Math.ceil(entries.length / RECIPES_PER_SITEMAP) + 1; // +1 for static pages
    return Array.from({ length: count }, (_, i) => ({ id: i }));
  } catch {
    return [{ id: 0 }];
  }
}

export default async function sitemap({
  id,
}: {
  id: number;
}): Promise<MetadataRoute.Sitemap> {
  // id=0: 정적 페이지
  if (id === 0) {
    return [
      {
        url: "https://recipe.eupori.dev",
        lastModified: new Date(),
        changeFrequency: "daily",
        priority: 1,
      },
      {
        url: "https://recipe.eupori.dev/recipes",
        lastModified: new Date(),
        changeFrequency: "daily",
        priority: 0.9,
      },
    ];
  }

  // id=1,2,3...: 레시피 페이지 (500개씩)
  try {
    const res = await fetch(`${API_BASE}/reference-recipes/sitemap`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];

    const entries: { id: number; crawled_at: string | null }[] =
      await res.json();
    const start = (id - 1) * RECIPES_PER_SITEMAP;
    const slice = entries.slice(start, start + RECIPES_PER_SITEMAP);

    return slice.map((entry) => ({
      url: `https://recipe.eupori.dev/recipes/${entry.id}`,
      lastModified: entry.crawled_at ? new Date(entry.crawled_at) : new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    }));
  } catch {
    return [];
  }
}
