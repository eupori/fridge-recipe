"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Package, Plus, X, ChefHat, Trash2 } from "lucide-react";

const STORAGE_KEY = "pantry-items";

// 자주 쓰는 재료 추천
const SUGGESTED_ITEMS = [
  "계란", "양파", "대파", "마늘", "김치", "두부",
  "당근", "감자", "고추", "버섯", "스팸", "참치캔",
  "밥", "라면", "어묵", "햄", "치즈", "우유"
];

export default function PantryPage() {
  const [items, setItems] = useState<string[]>([]);
  const [newItem, setNewItem] = useState("");
  const [isHydrated, setIsHydrated] = useState(false);

  // localStorage에서 로드
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setItems(JSON.parse(stored));
      }
    } catch {
      // ignore
    }
    setIsHydrated(true);
  }, []);

  // localStorage에 저장
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    }
  }, [items, isHydrated]);

  const addItem = (item: string) => {
    const trimmed = item.trim();
    if (trimmed && !items.includes(trimmed)) {
      setItems((prev) => [...prev, trimmed]);
    }
    setNewItem("");
  };

  const removeItem = (item: string) => {
    setItems((prev) => prev.filter((i) => i !== item));
  };

  const clearAll = () => {
    if (confirm("모든 재료를 삭제하시겠습니까?")) {
      setItems([]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addItem(newItem);
  };

  // 아직 추가되지 않은 추천 재료만 표시
  const availableSuggestions = SUGGESTED_ITEMS.filter((s) => !items.includes(s));

  return (
    <main className="container max-w-3xl mx-auto py-10 px-4">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <Package className="w-6 h-6" />
          <h1 className="text-3xl font-bold">보유 재료 관리</h1>
        </div>
        <p className="text-muted-foreground">
          냉장고에 있는 재료를 등록해두면 레시피 검색 시 바로 불러올 수 있어요
        </p>
      </div>

      <div className="grid gap-6">
        {/* 재료 추가 폼 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">재료 추가</CardTitle>
            <CardDescription>보유한 재료를 하나씩 추가하세요</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={newItem}
                onChange={(e) => setNewItem(e.target.value)}
                placeholder="예: 계란, 양파"
                className="flex-1"
              />
              <Button type="submit" disabled={!newItem.trim()}>
                <Plus className="w-4 h-4 mr-1" />
                추가
              </Button>
            </form>

            {/* 추천 재료 */}
            {availableSuggestions.length > 0 && (
              <div className="mt-4">
                <Label className="text-sm text-muted-foreground mb-2 block">
                  자주 쓰는 재료
                </Label>
                <div className="flex flex-wrap gap-2">
                  {availableSuggestions.slice(0, 12).map((item) => (
                    <Button
                      key={item}
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => addItem(item)}
                      className="h-7 text-xs"
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      {item}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 현재 보유 재료 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">내 재료 목록</CardTitle>
                <CardDescription>
                  {items.length}개의 재료가 등록되어 있습니다
                </CardDescription>
              </div>
              {items.length > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  전체 삭제
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {items.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Package className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>아직 등록된 재료가 없습니다</p>
                <p className="text-sm mt-1">위에서 재료를 추가해보세요</p>
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <Badge
                    key={item}
                    variant="secondary"
                    className="pl-3 pr-1 py-1.5 text-sm flex items-center gap-1"
                  >
                    {item}
                    <button
                      onClick={() => removeItem(item)}
                      className="ml-1 hover:bg-muted rounded p-0.5"
                      aria-label={`${item} 삭제`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 레시피 검색 바로가기 */}
        {items.length > 0 && (
          <Card className="bg-primary/5 border-primary/20">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ChefHat className="w-8 h-8 text-primary" />
                  <div>
                    <p className="font-medium">재료 준비 완료!</p>
                    <p className="text-sm text-muted-foreground">
                      {items.length}개의 재료로 레시피를 검색해보세요
                    </p>
                  </div>
                </div>
                <Button asChild>
                  <Link href="/">레시피 추천받기</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
