"use client";

import { useEffect, useRef } from "react";

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
  const containerRef = useRef<HTMLDivElement>(null);
  const pushed = useRef(false);

  useEffect(() => {
    if (pushed.current) return;

    const timer = setTimeout(() => {
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
        pushed.current = true;
      } catch {
        // adsbygoogle not loaded yet
      }
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className={className} ref={containerRef}>
      <ins
        className="adsbygoogle"
        style={{ display: "block", minHeight: "50px" }}
        data-ad-client="ca-pub-4539589433798899"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive="true"
      />
    </div>
  );
}
