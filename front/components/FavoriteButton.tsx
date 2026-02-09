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
  likeCount?: number;
  onFavoriteChange?: (isFavorite: boolean) => void;
};

function formatLikeCount(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1).replace(/\.0$/, "")}k`;
  }
  return count.toString();
}

export function FavoriteButton({ recommendationId, recipeIndex, recipeTitle, recipeImageUrl, likeCount = 0, onFavoriteChange }: Props) {
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
      // pendingFavorite 저장 (로그인 후 자동 즐겨찾기 처리용)
      const pendingFavorite = {
        recommendationId,
        recipeIndex,
        recipeTitle,
        recipeImageUrl,
        timestamp: Date.now()
      };
      localStorage.setItem("pendingFavorite", JSON.stringify(pendingFavorite));

      // returnUrl과 함께 로그인 페이지로 이동
      const currentPath = window.location.pathname;
      router.push(`/login?returnUrl=${encodeURIComponent(currentPath)}`);
      return;
    }

    setLoading(true);
    try {
      if (isFavorite && favoriteId) {
        await removeFavorite(favoriteId);
        setIsFavorite(false);
        setFavoriteId(null);
        onFavoriteChange?.(false);
      } else {
        const result = await addFavorite(recommendationId, recipeIndex, recipeTitle, recipeImageUrl);
        setIsFavorite(true);
        setFavoriteId(result.id);
        onFavoriteChange?.(true);
      }
    } catch (err) {
      console.error("즐겨찾기 처리 실패:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="icon"
        onClick={handleClick}
        disabled={loading}
        className={isFavorite ? "text-red-500 hover:text-red-600" : "text-muted-foreground hover:text-red-500"}
      >
        <Heart className={`w-5 h-5 ${isFavorite ? "fill-current" : ""}`} />
      </Button>
      {likeCount > 0 && (
        <span className="text-sm text-muted-foreground font-medium min-w-[1.5ch]">
          {formatLikeCount(likeCount)}
        </span>
      )}
    </div>
  );
}
