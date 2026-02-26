import type { MetadataRoute } from "next";

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // 정적 페이지
  const staticPages: MetadataRoute.Sitemap = [
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

  // 동적 레시피 페이지
  try {
    const res = await fetch(`${API_BASE}/reference-recipes/sitemap`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return staticPages;

    const entries: { id: number; crawled_at: string | null }[] = await res.json();
    const recipePages: MetadataRoute.Sitemap = entries.map((entry) => ({
      url: `https://recipe.eupori.dev/recipes/${entry.id}`,
      lastModified: entry.crawled_at ? new Date(entry.crawled_at) : new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.7,
    }));

    return [...staticPages, ...recipePages];
  } catch {
    return staticPages;
  }
}
