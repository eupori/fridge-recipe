"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Package, Heart, User } from "lucide-react";

const tabs = [
  { href: "/", icon: Home, label: "홈" },
  { href: "/pantry", icon: Package, label: "보유재료" },
  { href: "/favorites", icon: Heart, label: "즐겨찾기" },
  { href: "/login", icon: User, label: "내정보" },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-background/95 backdrop-blur-sm border-t sm:hidden z-40"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex justify-around items-center h-14">
        {tabs.map((tab) => {
          const isActive = pathname === tab.href;
          const Icon = tab.icon;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 transition-colors ${
                isActive ? "text-primary" : "text-muted-foreground"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
