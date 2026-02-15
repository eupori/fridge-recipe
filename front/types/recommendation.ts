export interface ReferenceVideo {
  video_id: string;
  title: string;
  channel: string;
  view_count: number;
  thumbnail_url: string;
}

export interface Recipe {
  title: string;
  time_min: number;
  servings: number;
  summary: string;
  image_url: string | null;
  ingredients_total: string[];
  ingredients_have: string[];
  ingredients_need: string[];
  steps: string[];
  tips: string[];
  warnings: string[];
  // 정밀 모드 전용 필드
  nutrition?: {
    calories: string;
    protein: string;
    carbs: string;
    fat: string;
  } | null;
  substitutes?: string[];
  storage_tip?: string | null;
  reference_video?: ReferenceVideo | null;
}

export interface ShoppingItem {
  item: string;
  qty: number | null;
  unit: string | null;
  category: string | null;
  purchase_url: string | null;
}

export interface Recommendation {
  id: string;
  created_at: string;
  quality_level?: string;
  recipes: Recipe[];
  shopping_list: ShoppingItem[];
}
