"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ApertureIcon, ChatCircleDotsIcon } from "@phosphor-icons/react";
import { openChat } from "@/components/chat/chat-bus";

const NAV = [
  { href: "/#mirrorless", label: "Mirrorless" },
  { href: "/#dslr", label: "DSLR" },
  { href: "/#cinema", label: "Cinema" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-4 md:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <ApertureIcon size={26} weight="light" className="text-accent" />
          <span className="font-display text-lg tracking-tight">
            Obscura
            <span className="ml-2 hidden text-xs font-sans uppercase tracking-[0.2em] text-faint sm:inline">
              Fine Camera Supply
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`text-sm transition-colors hover:text-foreground ${
                pathname === item.href ? "text-foreground" : "text-muted"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <button
          onClick={() => openChat()}
          className="flex items-center gap-2 rounded-full border border-foreground/15 bg-foreground px-4 py-2 text-sm text-background transition-transform hover:bg-foreground/90 active:scale-[0.98]"
        >
          <ChatCircleDotsIcon size={16} weight="regular" />
          <span>Ask the clerk</span>
        </button>
      </div>
    </header>
  );
}
