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

// Auth types
export type UserResponse = {
  id: string;
  email: string;
  nickname: string | null;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

// Token management
function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function setToken(token: string): void {
  localStorage.setItem("access_token", token);
}

function removeToken(): void {
  localStorage.removeItem("access_token");
}

function getAuthHeaders(): HeadersInit {
  const token = getToken();
  if (token) {
    return { "Authorization": `Bearer ${token}` };
  }
  return {};
}

// Auth API
export async function signup(email: string, password: string): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  setToken(data.access_token);
  return data;
}

export async function getMe(): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    throw new Error("인증이 필요합니다.");
  }
  return res.json();
}

export function logout(): void {
  removeToken();
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

// Recommendation API
export async function createRecommendation(payload: RecommendationCreate) {
  const res = await fetch(`${API_BASE}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getRecommendation(id: string) {
  const res = await fetch(`${API_BASE}/recommendations/${id}`, {
    cache: "no-store",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  return res.json();
}

// Favorite types
export type FavoriteResponse = {
  id: string;
  recommendation_id: string;
  recipe_index: number;
  recipe_title: string;
  recipe_image_url: string | null;
  created_at: string;
};

export type FavoriteCheck = {
  is_favorite: boolean;
  favorite_id: string | null;
};

// Favorites API
export async function addFavorite(
  recommendationId: string,
  recipeIndex: number,
  recipeTitle: string,
  recipeImageUrl: string | null
): Promise<FavoriteResponse> {
  const res = await fetch(`${API_BASE}/favorites`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      recommendation_id: recommendationId,
      recipe_index: recipeIndex,
      recipe_title: recipeTitle,
      recipe_image_url: recipeImageUrl,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getFavorites(): Promise<FavoriteResponse[]> {
  const res = await fetch(`${API_BASE}/favorites`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    throw new Error("즐겨찾기를 불러올 수 없습니다.");
  }
  return res.json();
}

export async function removeFavorite(favoriteId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/favorites/${favoriteId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

export async function checkFavorite(
  recommendationId: string,
  recipeIndex: number
): Promise<FavoriteCheck> {
  const params = new URLSearchParams({
    recommendation_id: recommendationId,
    recipe_index: recipeIndex.toString(),
  });
  const res = await fetch(`${API_BASE}/favorites/check?${params}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    return { is_favorite: false, favorite_id: null };
  }
  return res.json();
}
