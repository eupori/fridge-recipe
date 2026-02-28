import type { ShoppingItem } from "@/types/recommendation";

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

const API_ROOT = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE = `${API_ROOT}/api/v1`;

/** /static/... 경로를 백엔드 절대 URL로 변환 */
export function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("/static/")) return `${API_ROOT}${url}`;
  return url;
}

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
    throw new Error(res.status === 401 ? "UNAUTHORIZED" : `HTTP ${res.status}`);
  }
  return res.json();
}

export function logout(): void {
  removeToken();
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

// Rate limit error
export class RateLimitError extends Error {
  remaining: number;
  constructor(message: string, remaining: number) {
    super(message);
    this.name = "RateLimitError";
    this.remaining = remaining;
  }
}

// Recommendation API
export async function createRecommendation(payload: RecommendationCreate) {
  const res = await fetch(`${API_BASE}/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });

  if (res.status === 429) {
    const data = await res.json().catch(() => ({}));
    throw new RateLimitError(
      data.detail || "일일 무료 이용 횟수를 초과했습니다.",
      data.remaining ?? 0,
    );
  }

  // Parse remaining count from header
  const remaining = res.headers.get("X-Daily-Remaining");

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  const result = await res.json();
  // Attach remaining info to the result
  if (remaining !== null) {
    result._dailyRemaining = parseInt(remaining, 10);
  }
  return result;
}

// Async recommendation API
export type JobStatusResponse = {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  recommendation_id: string | null;
  error: string | null;
};

export async function createRecommendationAsync(
  payload: RecommendationCreate
): Promise<{ job_id: string | null; recommendation_id: string | null; _dailyRemaining?: number }> {
  const res = await fetch(`${API_BASE}/recommendations/async`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });

  if (res.status === 429) {
    const data = await res.json().catch(() => ({}));
    throw new RateLimitError(
      data.detail || "일일 무료 이용 횟수를 초과했습니다.",
      data.remaining ?? 0,
    );
  }

  const remaining = res.headers.get("X-Daily-Remaining");

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  const result = await res.json();
  if (remaining !== null) {
    result._dailyRemaining = parseInt(remaining, 10);
  }
  return result;
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/recommendations/jobs/${jobId}`);
  if (!res.ok) {
    throw new Error(`Job 조회 실패: HTTP ${res.status}`);
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

// Like stats types
export type RecipeLikeCount = {
  recipe_index: number;
  like_count: number;
};

export type RecommendationLikeStats = {
  recommendation_id: string;
  recipes: RecipeLikeCount[];
};

export async function getRecipeLikeStats(
  recommendationId: string
): Promise<RecommendationLikeStats> {
  const res = await fetch(`${API_BASE}/favorites/stats/${recommendationId}`);
  if (!res.ok) {
    // 에러 시 기본값 반환
    return {
      recommendation_id: recommendationId,
      recipes: [
        { recipe_index: 0, like_count: 0 },
        { recipe_index: 1, like_count: 0 },
        { recipe_index: 2, like_count: 0 },
      ],
    };
  }
  return res.json();
}

// Search History types
export type SearchHistoryResponse = {
  id: string;
  recommendation_id: string;
  ingredients: string[];
  time_limit_min: number;
  servings: number;
  recipe_titles: string[];
  recipe_images: (string | null)[];
  searched_at: string;
};

// Search History API
export async function getSearchHistories(limit?: number): Promise<SearchHistoryResponse[]> {
  const params = limit ? `?limit=${limit}` : "";
  const res = await fetch(`${API_BASE}/search-histories${params}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    return [];
  }
  return res.json();
}

export async function deleteSearchHistory(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/search-histories/${id}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

// Image API
export async function getRecipeImage(title: string): Promise<string | null> {
  try {
    const params = new URLSearchParams({ title });
    const res = await fetch(`${API_BASE}/images/generate?${params}`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.image_url ?? null;
  } catch {
    return null;
  }
}

export type BatchImageResult = {
  title: string;
  image_url: string | null;
};

export async function getRecipeImages(
  titles: string[],
  recommendationId?: string
): Promise<BatchImageResult[]> {
  try {
    const body: { titles: string[]; recommendation_id?: string } = { titles };
    if (recommendationId) {
      body.recommendation_id = recommendationId;
    }
    const res = await fetch(`${API_BASE}/images/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) return titles.map((t) => ({ title: t, image_url: null }));
    const data = await res.json();
    return data.images ?? [];
  } catch {
    return titles.map((t) => ({ title: t, image_url: null }));
  }
}

// Stats API
export type StatsResponse = {
  total_recipes_generated: number;
  total_users: number;
};

export async function getStats(): Promise<StatsResponse> {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) return { total_recipes_generated: 0, total_users: 0 };
    return res.json();
  } catch {
    return { total_recipes_generated: 0, total_users: 0 };
  }
}

export async function clearAllSearchHistories(): Promise<{ deleted_count: number }> {
  const res = await fetch(`${API_BASE}/search-histories/all`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Rating types
export type RecipeRatingStats = {
  recipe_index: number;
  average_rating: number;
  count: number;
  my_rating: number | null;
};

export type RecommendationRatingStats = {
  recommendation_id: string;
  recipes: RecipeRatingStats[];
};

// Rating API
export async function rateRecipe(
  recommendationId: string,
  recipeIndex: number,
  rating: number
): Promise<void> {
  const res = await fetch(`${API_BASE}/ratings`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      recommendation_id: recommendationId,
      recipe_index: recipeIndex,
      rating,
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

export async function getRatingStats(
  recommendationId: string
): Promise<RecommendationRatingStats> {
  const res = await fetch(`${API_BASE}/ratings/${recommendationId}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    return {
      recommendation_id: recommendationId,
      recipes: [
        { recipe_index: 0, average_rating: 0, count: 0, my_rating: null },
        { recipe_index: 1, average_rating: 0, count: 0, my_rating: null },
        { recipe_index: 2, average_rating: 0, count: 0, my_rating: null },
      ],
    };
  }
  return res.json();
}

// Reference Recipe types
export type ReferenceRecipeListItem = {
  id: number;
  title: string;
  category: string;
  key_ingredients: string[];
  time_min: number | null;
  servings: number | null;
  view_count: number;
  source: string;
};

export type ReferenceRecipeDetail = {
  id: number;
  title: string;
  category: string;
  key_ingredients: string[];
  all_ingredients: string[];
  steps: string[];
  technique: string | null;
  time_min: number | null;
  servings: number | null;
  view_count: number;
  rating: number | null;
  source: string;
  source_url: string;
  crawled_at: string | null;
};

export type ReferenceRecipeListResponse = {
  items: ReferenceRecipeListItem[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export type CategoryCount = {
  category: string;
  count: number;
};

export type SitemapEntry = {
  id: number;
  title: string;
  category: string;
  crawled_at: string | null;
};

// Reference Recipe API (서버 컴포넌트용 — no auth needed)
export async function getReferenceRecipes(params?: {
  category?: string;
  page?: number;
  per_page?: number;
}): Promise<ReferenceRecipeListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.per_page) searchParams.set("per_page", params.per_page.toString());
  const qs = searchParams.toString();
  const res = await fetch(`${API_BASE}/reference-recipes${qs ? `?${qs}` : ""}`, {
    next: { revalidate: 86400 },
  });
  if (!res.ok) {
    return { items: [], total: 0, page: 1, per_page: 20, total_pages: 1 };
  }
  return res.json();
}

export async function getReferenceRecipe(id: number): Promise<ReferenceRecipeDetail | null> {
  const res = await fetch(`${API_BASE}/reference-recipes/${id}`, {
    next: { revalidate: 86400 },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function getReferenceRecipeCategories(): Promise<CategoryCount[]> {
  const res = await fetch(`${API_BASE}/reference-recipes/categories`, {
    next: { revalidate: 86400 },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getReferenceRecipeSitemap(): Promise<SitemapEntry[]> {
  const res = await fetch(`${API_BASE}/reference-recipes/sitemap`, {
    next: { revalidate: 86400 },
  });
  if (!res.ok) return [];
  return res.json();
}

// Meal Plan types
export type MealSlotResponse = {
  id: string;
  day_of_week: number;
  meal_type: string;
  recommendation_id: string;
  recipe_index: number;
  recipe_title: string;
  recipe_image_url: string | null;
};

export type MealPlanResponse = {
  id: string;
  title: string;
  week_start: string;
  slots: MealSlotResponse[];
  created_at: string;
  updated_at: string;
};

export type MealPlanListItem = {
  id: string;
  title: string;
  week_start: string;
  slot_count: number;
  created_at: string;
};

// Meal Plan API
export async function createMealPlan(
  title: string,
  weekStart: string
): Promise<MealPlanResponse> {
  const res = await fetch(`${API_BASE}/meal-plans`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ title, week_start: weekStart }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getMealPlans(): Promise<MealPlanListItem[]> {
  const res = await fetch(`${API_BASE}/meal-plans`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) return [];
  return res.json();
}

export async function getMealPlan(
  id: string
): Promise<MealPlanResponse | null> {
  const res = await fetch(`${API_BASE}/meal-plans/${id}`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) return null;
  return res.json();
}

export async function deleteMealPlan(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/meal-plans/${id}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

export async function addMealSlot(
  planId: string,
  dayOfWeek: number,
  mealType: string,
  recommendationId: string,
  recipeIndex: number,
  recipeTitle: string,
  recipeImageUrl: string | null
): Promise<MealSlotResponse> {
  const res = await fetch(`${API_BASE}/meal-plans/${planId}/slots`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({
      day_of_week: dayOfWeek,
      meal_type: mealType,
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

export async function removeMealSlot(
  planId: string,
  slotId: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/meal-plans/${planId}/slots/${slotId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

export async function getMealPlanShoppingList(
  planId: string
): Promise<ShoppingItem[]> {
  const res = await fetch(`${API_BASE}/meal-plans/${planId}/shopping-list`, {
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) return [];
  return res.json();
}
