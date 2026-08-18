"use client";

import { ChatCircleDotsIcon } from "@phosphor-icons/react";
import { openChat } from "@/components/chat/chat-bus";

export function AskClerkCta({
  prompt,
  label,
  variant = "solid",
}: {
  prompt?: string;
  label: string;
  variant?: "solid" | "outline";
}) {
  const base =
    "inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm transition-all active:scale-[0.98]";
  const styles =
    variant === "solid"
      ? "bg-foreground text-background hover:bg-foreground/90"
      : "border border-foreground/20 text-foreground hover:border-foreground/50";
  return (
    <button onClick={() => openChat(prompt)} className={`${base} ${styles}`}>
      <ChatCircleDotsIcon size={17} />
      <span>{label}</span>
    </button>
  );
}
