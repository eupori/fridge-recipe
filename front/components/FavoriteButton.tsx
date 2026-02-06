"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { addFavorite, removeFavorite, checkFavorite } from "@/lib/api";

type Props = {
  recommendationId: string;
  recipeIndex: number;
  recipeTitle: string;
  recipeImageUrl: string | null;
};

export function FavoriteButton({ recommendationId, recipeIndex, recipeTitle, recipeImageUrl }: Props) {
  const { user } = useAuth();
  const router = useRouter();
  const [isFavorite, setIsFavorite] = useState(false);
  const [favoriteId, setFavoriteId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!user) {
      setIsFavorite(false);
      setFavoriteId(null);
      return;
    }

    checkFavorite(recommendationId, recipeIndex).then((result) => {
      setIsFavorite(result.is_favorite);
      setFavoriteId(result.favorite_id);
    });
  }, [user, recommendationId, recipeIndex]);

  const handleClick = async () => {
    if (!user) {
      router.push("/login");
      return;
    }

    setLoading(true);
    try {
      if (isFavorite && favoriteId) {
        await removeFavorite(favoriteId);
        setIsFavorite(false);
        setFavoriteId(null);
      } else {
        const result = await addFavorite(recommendationId, recipeIndex, recipeTitle, recipeImageUrl);
        setIsFavorite(true);
        setFavoriteId(result.id);
      }
    } catch (err) {
      console.error("즐겨찾기 처리 실패:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={handleClick}
      disabled={loading}
      className={isFavorite ? "text-red-500 hover:text-red-600" : "text-muted-foreground hover:text-red-500"}
    >
      <Heart className={`w-5 h-5 ${isFavorite ? "fill-current" : ""}`} />
    </Button>
  );
}
