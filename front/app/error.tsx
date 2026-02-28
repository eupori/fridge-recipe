"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("페이지 오류:", error);
  }, [error]);

  return (
    <main className="container max-w-lg mx-auto px-4 py-20 text-center">
      <h2 className="text-xl font-bold mb-3">문제가 발생했습니다</h2>
      <p className="text-muted-foreground mb-6 text-sm">
        일시적인 오류입니다. 아래 버튼을 눌러 다시 시도해주세요.
      </p>
      <button
        onClick={reset}
        className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 transition-opacity"
      >
        다시 시도
      </button>
    </main>
  );
}
