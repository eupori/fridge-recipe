"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getFavorites, removeFavorite, resolveImageUrl, FavoriteResponse } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Heart, Trash2, ChefHat } from "lucide-react";

export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      router.push("/login");
      return;
    }

    loadFavorites();
  }, [user, authLoading, router]);

  const loadFavorites = async () => {
    setLoading(true);
    try {
      const data = await getFavorites();
      setFavorites(data);
    } catch (err: any) {
      setError(err.message || "즐겨찾기를 불러올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (favoriteId: string) => {
    try {
      await removeFavorite(favoriteId);
      setFavorites((prev) => prev.filter((f) => f.id !== favoriteId));
    } catch (err: any) {
      console.error("삭제 실패:", err);
    }
  };

  if (authLoading || loading) {
    return (
      <main className="container max-w-3xl mx-auto py-10 px-4">
        <p className="text-muted-foreground">불러오는 중...</p>
      </main>
    );
  }

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Heart className="w-6 h-6 text-red-500 fill-red-500" />
          <h1 className="text-3xl font-bold">내 즐겨찾기</h1>
        </div>
        <p className="text-muted-foreground">저장한 레시피를 확인하세요</p>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md mb-6">
          {error}
        </div>
      )}

      {favorites.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <ChefHat className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">아직 즐겨찾기한 레시피가 없습니다</p>
            <Button asChild>
              <Link href="/">레시피 추천받기</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {favorites.map((favorite) => (
            <Card key={favorite.id} className="overflow-hidden">
              <div className="flex">
                {resolveImageUrl(favorite.recipe_image_url) && (
                  <div className="w-24 h-24 md:w-32 md:h-32 shrink-0 bg-muted">
                    <img
                      src={resolveImageUrl(favorite.recipe_image_url)!}
                      alt={favorite.recipe_title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}

                <div className="flex-1 p-4 flex flex-col justify-between">
                  <div>
                    <h3 className="font-bold text-lg mb-1">{favorite.recipe_title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {new Date(favorite.created_at).toLocaleDateString("ko-KR")}에 저장
                    </p>
                  </div>

                  <div className="flex items-center gap-2 mt-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/r/${favorite.recommendation_id}`}>
                        레시피 보기
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemove(favorite.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
