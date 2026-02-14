"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Share2, Check, MessageCircle } from "lucide-react";

declare global {
  interface Window {
    Kakao?: {
      isInitialized: () => boolean;
      init: (key: string) => void;
      Share: {
        sendDefault: (options: Record<string, unknown>) => void;
      };
    };
  }
}

interface ShareButtonProps {
  title: string;
  text?: string;
  url?: string;
  imageUrl?: string;
}

function initKakao() {
  const key = process.env.NEXT_PUBLIC_KAKAO_JS_KEY;
  if (!key || !window.Kakao) return false;
  if (!window.Kakao.isInitialized()) {
    window.Kakao.init(key);
  }
  return window.Kakao.isInitialized();
}

export function ShareButton({ title, text, url, imageUrl }: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    const shareUrl = url || window.location.href;
    const shareData = { title, text: text || title, url: shareUrl };

    if (navigator.share) {
      try {
        await navigator.share(shareData);
      } catch {
        // 사용자가 공유 취소
      }
    } else {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleKakaoShare = useCallback(() => {
    if (!initKakao()) {
      // 카카오 SDK 로드 실패 시 일반 공유로 fallback
      handleShare();
      return;
    }

    const shareUrl = url || window.location.href;
    window.Kakao!.Share.sendDefault({
      objectType: "feed",
      content: {
        title,
        description: text || "냉장고 재료로 만드는 15분 레시피",
        imageUrl: imageUrl || "https://recipe.eupori.dev/og-image.png",
        link: { mobileWebUrl: shareUrl, webUrl: shareUrl },
      },
      buttons: [
        {
          title: "레시피 보기",
          link: { mobileWebUrl: shareUrl, webUrl: shareUrl },
        },
      ],
    });
  }, [title, text, url, imageUrl]);

  return (
    <div className="flex items-center gap-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={handleKakaoShare}
        className="h-8 w-8 p-0"
        title="카카오톡 공유"
      >
        <MessageCircle className="w-4 h-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleShare}
        className="h-8 w-8 p-0"
        title="공유하기"
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-500" />
        ) : (
          <Share2 className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
}
