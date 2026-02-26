import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "오머먹 레시피";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

export default async function Image({ params }: { params: { id: string } }) {
  let title = "레시피";
  let category = "";
  let ingredients: string[] = [];

  try {
    const res = await fetch(`${API_BASE}/reference-recipes/${params.id}`);
    if (res.ok) {
      const data = await res.json();
      title = data.title ?? "레시피";
      category = data.category ?? "";
      ingredients = data.key_ingredients ?? [];
    }
  } catch {
    // fallback
  }

  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
          padding: "40px",
        }}
      >
        {category && (
          <div
            style={{
              fontSize: 24,
              color: "#3b82f6",
              marginBottom: 16,
              display: "flex",
              padding: "4px 16px",
              borderRadius: "9999px",
              backgroundColor: "rgba(59,130,246,0.1)",
            }}
          >
            {category}
          </div>
        )}
        <div
          style={{
            fontSize: 52,
            fontWeight: 800,
            color: "#0f172a",
            marginBottom: 20,
            display: "flex",
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          {title}
        </div>
        {ingredients.length > 0 && (
          <div
            style={{
              display: "flex",
              gap: "8px",
              marginBottom: 24,
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            {ingredients.slice(0, 5).map((ing) => (
              <span
                key={ing}
                style={{
                  fontSize: 20,
                  color: "#64748b",
                  padding: "4px 12px",
                  borderRadius: "8px",
                  backgroundColor: "rgba(0,0,0,0.05)",
                  display: "flex",
                }}
              >
                {ing}
              </span>
            ))}
          </div>
        )}
        <div
          style={{
            fontSize: 22,
            color: "#94a3b8",
            display: "flex",
            marginTop: 12,
          }}
        >
          오머먹 — 냉장고 열면, 답 나온다
        </div>
      </div>
    ),
    { ...size }
  );
}
