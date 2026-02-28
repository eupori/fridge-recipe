"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";

declare global {
  interface Window {
    adsbygoogle: any[];
  }
}

interface AdUnitProps {
  slot: string;
  format?: string;
  className?: string;
}

export default function AdUnit({ slot, format = "auto", className }: AdUnitProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let attempts = 0;
    const maxAttempts = 5;

    const tryPush = () => {
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      } catch {
        if (attempts < maxAttempts) {
          attempts++;
          setTimeout(tryPush, 500 * attempts);
        }
      }
    };

    const timer = setTimeout(tryPush, 200);
    return () => clearTimeout(timer);
  }, [pathname]);

  return (
    <div className={`overflow-hidden ${className ?? ""}`} ref={containerRef}>
      <ins
        key={`${slot}-${pathname}`}
        className="adsbygoogle"
        style={{ display: "block", minHeight: "50px", maxWidth: "100%" }}
        data-ad-client="ca-pub-4539589433798899"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive="true"
      />
    </div>
  );
}
