type Constraints = {
  time_limit_min: number;
  servings: number;
  tools: string[];
  exclude: string[];
};

export type RecommendationCreate = {
  ingredients: string[];
  constraints: Constraints;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export async function createRecommendation(payload: RecommendationCreate) {
  const res = await fetch(`${API_BASE}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getRecommendation(id: string) {
  const res = await fetch(`${API_BASE}/recommendations/${id}`, { cache: "no-store" });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json();
}
