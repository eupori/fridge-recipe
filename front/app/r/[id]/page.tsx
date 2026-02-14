import type { Metadata } from "next";
import ResultClient from "./ResultClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";
const API_ROOT = API_BASE.replace(/\/api\/v\d+$/, "");

function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("/static/")) return `${API_ROOT}${url}`;
  return url;
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  try {
    const res = await fetch(`${API_BASE}/recommendations/${params.id}`, {
      cache: "no-store",
    });
    if (!res.ok) throw new Error();
    const data = await res.json();

    const titles = data.recipes?.map((r: { title: string }) => r.title).join(", ") ?? "";
    const firstImage = resolveImageUrl(data.recipes?.[0]?.image_url);

    return {
      title: `${titles} | 냉장고 레시피`,
      description: `냉장고 재료로 만드는 15분 레시피: ${titles}`,
      openGraph: {
        title: titles,
        description: `냉장고 재료로 만드는 15분 레시피: ${titles}`,
        ...(firstImage ? { images: [firstImage] } : {}),
      },
    };
  } catch {
    return {
      title: "추천 레시피 | 냉장고 레시피",
      description: "AI가 추천한 냉장고 재료 기반 레시피",
    };
  }
}

export default function ResultPage({ params }: { params: { id: string } }) {
  return <ResultClient id={params.id} />;
}
