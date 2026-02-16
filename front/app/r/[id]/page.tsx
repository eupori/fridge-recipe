import type { Metadata } from "next";
import { resolveImageUrl } from "@/lib/api";
import ResultClient from "./ResultClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

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

export default function ResultPage({ params }: { params: { id: string } }) {
  return <ResultClient id={params.id} />;
}
