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
  recipes: Recipe[];
  shopping_list: ShoppingItem[];
}
