"use client";

import { memo, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ImageDown, Loader2 } from "lucide-react";
import html2canvas from "html2canvas";

interface SaveCardButtonProps {
  recipe: {
    title: string;
    time_min: number;
    servings: number;
    ingredients_have?: string[];
    ingredients_need?: string[];
    steps?: string[];
    tips?: string[];
  };
  imageUrl?: string | null;
  recipeNumber: number;
}

export const SaveCardButton = memo(function SaveCardButton({
  recipe,
  imageUrl,
  recipeNumber,
}: SaveCardButtonProps) {
  const [saving, setSaving] = useState(false);

  const handleSave = useCallback(async () => {
    if (saving) return;
    setSaving(true);

    try {
      // 이미지를 base64로 변환 (CORS 우회)
      let base64Image: string | null = null;
      if (imageUrl) {
        try {
          const res = await fetch(imageUrl);
          const blob = await res.blob();
          base64Image = await new Promise<string>((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result as string);
            reader.readAsDataURL(blob);
          });
        } catch {
          // 이미지 로드 실패 시 무시
        }
      }

      // 캡처용 카드를 임시로 DOM에 추가
      const container = document.createElement("div");
      container.style.position = "fixed";
      container.style.left = "-9999px";
      container.style.top = "0";
      document.body.appendChild(container);

      // 카드 렌더링
      const card = document.createElement("div");
      card.style.width = "540px";
      card.style.fontFamily =
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      card.style.background = "#ffffff";
      card.style.borderRadius = "16px";
      card.style.overflow = "hidden";

      const steps = recipe.steps || [];
      const tips = recipe.tips || [];
      const haveCount = recipe.ingredients_have?.length || 0;
      const needCount = recipe.ingredients_need?.length || 0;

      card.innerHTML = `
        <div style="position:relative;">
          ${
            base64Image
              ? `<img src="${base64Image}" style="width:540px;height:300px;object-fit:cover;display:block;" />`
              : `<div style="width:540px;height:180px;background:linear-gradient(135deg,#f97316,#ea580c);display:flex;align-items:center;justify-content:center;">
                  <span style="font-size:64px;">🍳</span>
                </div>`
          }
          <div style="position:absolute;top:16px;left:16px;background:rgba(0,0,0,0.6);color:#fff;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600;">
            레시피 ${recipeNumber}
          </div>
        </div>
        <div style="padding:24px;">
          <h2 style="font-size:24px;font-weight:700;margin:0 0 12px 0;color:#111;">${recipe.title}</h2>
          <div style="display:flex;gap:16px;margin-bottom:16px;color:#666;font-size:14px;">
            <span>⏱ ${recipe.time_min}분</span>
            <span>👤 ${recipe.servings}인분</span>
            <span style="color:#22c55e;">✓ 보유 ${haveCount}개</span>
            ${needCount > 0 ? `<span style="color:#f97316;">+ 추가 ${needCount}개</span>` : ""}
          </div>
          <div style="border-top:1px solid #e5e7eb;padding-top:16px;margin-bottom:${tips.length > 0 ? "16px" : "0"};">
            <div style="font-size:15px;font-weight:600;color:#111;margin-bottom:12px;">조리 순서</div>
            ${steps
              .map(
                (s, i) => `
              <div style="display:flex;gap:10px;margin-bottom:10px;font-size:14px;color:#333;line-height:1.5;">
                <span style="background:#f1f5f9;color:#64748b;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0;">${i + 1}</span>
                <span style="flex:1;">${s}</span>
              </div>`
              )
              .join("")}
          </div>
          ${
            tips.length > 0
              ? `
            <div style="border-top:1px solid #e5e7eb;padding-top:16px;">
              <div style="font-size:15px;font-weight:600;color:#111;margin-bottom:8px;">💡 팁</div>
              ${tips.map((t) => `<div style="font-size:13px;color:#666;margin-bottom:4px;">• ${t}</div>`).join("")}
            </div>`
              : ""
          }
          <div style="border-top:1px solid #e5e7eb;margin-top:16px;padding-top:12px;display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:13px;color:#9ca3af;">냉탐정 — 냉장고 열면, 답 나온다</span>
            <span style="font-size:12px;color:#9ca3af;">recipe.eupori.dev</span>
          </div>
        </div>
      `;

      container.appendChild(card);

      const canvas = await html2canvas(card, {
        scale: 2,
        backgroundColor: "#ffffff",
      });

      document.body.removeChild(container);

      // 다운로드
      const link = document.createElement("a");
      link.download = `${recipe.title.replace(/[^\w가-힣]/g, "_")}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch (err) {
      console.error("이미지 저장 실패:", err);
    } finally {
      setSaving(false);
    }
  }, [saving, recipe, imageUrl, recipeNumber]);

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleSave}
      className="h-9 w-9 p-0"
      title="이미지로 저장"
      disabled={saving}
    >
      {saving ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <ImageDown className="w-4 h-4" />
      )}
    </Button>
  );
});
