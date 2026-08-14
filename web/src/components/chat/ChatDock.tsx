"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ApertureIcon,
  ArrowUpIcon,
  ChatCircleDotsIcon,
  FilePdfIcon,
  WarningCircleIcon,
  XIcon,
} from "@phosphor-icons/react";
import { CHAT_EVENT, ChatEventDetail } from "./chat-bus";
import { ProductPreview } from "./ProductPreview";
import type { ChatProduct, Message } from "./types";

const SUGGESTIONS = [
  "What's the best camera for wildlife under 2000 EUR?",
  "How do I set up back-button focus on the Sony a7 IV?",
  "Compare the Nikon Z8 and the Canon EOS R5 Mark II",
  "Explain aperture like I'm new to photography",
];

let idCounter = 0;
const nextId = () => `msg-${++idCounter}-${Date.now()}`;

function ThinkingBubble() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2.5 self-start rounded-2xl rounded-bl-md bg-card px-4 py-3"
    >
      <ApertureIcon size={16} className="animate-spin text-accent [animation-duration:2.5s]" />
      <span className="text-sm text-muted">Checking the shelves</span>
      <span className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1 w-1 rounded-full bg-faint"
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </span>
    </motion.div>
  );
}

function MessageRow({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
        className="max-w-[85%] self-end rounded-2xl rounded-br-md bg-foreground px-4 py-2.5 text-sm leading-relaxed text-background"
      >
        {message.content}
      </motion.div>
    );
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
      className="flex max-w-[95%] flex-col gap-2.5 self-start"
    >
      <div
        className={`chat-prose rounded-2xl rounded-bl-md px-4 py-3 text-sm leading-relaxed ${
          message.error
            ? "border border-red-200 bg-red-50 text-red-800"
            : "bg-card text-foreground"
        }`}
      >
        {message.error && (
          <WarningCircleIcon size={16} className="mb-1 inline-block text-red-500" />
        )}
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
      </div>

      {message.products && message.products.length > 0 && (
        <div className="flex flex-col gap-2">
          {message.products.map((p, i) => (
            <ProductPreview key={p.slug} product={p} index={i} />
          ))}
        </div>
      )}

      {message.sources && message.sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-1">
          {message.sources.map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-[10px] text-faint"
            >
              <FilePdfIcon size={11} />
              {s}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export function ChatDock() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // The agent keeps the conversation; we only need the key to it.
  const threadIdRef = useRef<string | undefined>(undefined);
  const inFlightRef = useRef(false);

  const send = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    // Two sends in flight on a first turn would each start their own thread, and only
    // one id survives — the other conversation is orphaned server-side. The input is
    // disabled while loading, but suggestion buttons and the chat bus can still fire.
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    const userMsg: Message = { id: nextId(), role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, threadId: threadIdRef.current }),
      });
      const data: {
        answer?: string;
        sources?: string[];
        threadId?: string;
        products?: ChatProduct[];
        error?: string;
      } = await res.json();
      if (data.threadId) threadIdRef.current = data.threadId;
      if (!res.ok || data.error || !data.answer) {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: data.error ?? "Something went wrong. Please try again.",
            error: true,
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: data.answer!,
            products: data.products,
            sources: data.sources,
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: "Could not reach the store. Check your connection and try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<ChatEventDetail>).detail;
      setOpen(true);
      if (detail?.prompt) void send(detail.prompt);
    };
    window.addEventListener(CHAT_EVENT, handler);
    return () => window.removeEventListener(CHAT_EVENT, handler);
  }, [send]);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open, loading]);

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            key="fab"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            onClick={() => setOpen(true)}
            aria-label="Open store clerk chat"
            className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-foreground text-background shadow-[0_12px_30px_-10px_rgba(28,25,23,0.45)] transition-transform hover:scale-105 active:scale-95"
          >
            <ChatCircleDotsIcon size={24} weight="regular" />
            <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-background bg-emerald-500 animate-breathe" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 24, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 160, damping: 22 }}
            role="dialog"
            aria-label="Store clerk chat"
            className="fixed inset-x-0 bottom-0 z-50 flex h-[85dvh] flex-col overflow-hidden rounded-t-3xl border border-line bg-background shadow-[0_-10px_50px_-15px_rgba(28,25,23,0.25)] sm:inset-x-auto sm:bottom-5 sm:right-5 sm:h-[640px] sm:max-h-[calc(100dvh-40px)] sm:w-[420px] sm:rounded-3xl sm:shadow-[0_25px_60px_-15px_rgba(28,25,23,0.3)]"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-card">
                  <ApertureIcon size={20} weight="light" className="text-accent" />
                </div>
                <div>
                  <p className="text-sm font-medium leading-tight">The Clerk</p>
                  <p className="flex items-center gap-1.5 text-[11px] text-faint">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-breathe" />
                    Knows the catalog and the manuals
                  </p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close chat"
                className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-card hover:text-foreground"
              >
                <XIcon size={16} />
              </button>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
              {messages.length === 0 && !loading ? (
                <div className="flex h-full flex-col justify-end gap-6">
                  <div>
                    <p className="font-display text-xl leading-snug">
                      Afternoon. Looking for
                      <br />
                      anything in particular?
                    </p>
                    <p className="mt-2 max-w-[36ch] text-sm leading-relaxed text-muted">
                      Prices, stock, spec comparisons — or how-to questions straight from
                      the camera manuals.
                    </p>
                  </div>
                  <div className="flex flex-col gap-2">
                    {SUGGESTIONS.map((s, i) => (
                      <motion.button
                        key={s}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.15 + i * 0.07 }}
                        onClick={() => void send(s)}
                        className="rounded-2xl border border-line px-3.5 py-2.5 text-left text-sm text-muted transition-colors hover:border-foreground/30 hover:text-foreground active:scale-[0.99]"
                      >
                        {s}
                      </motion.button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {messages.map((m) => (
                    <MessageRow key={m.id} message={m} />
                  ))}
                  {loading && <ThinkingBubble />}
                </div>
              )}
            </div>

            {/* Input */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!loading) void send(input);
              }}
              className="border-t border-line p-3"
            >
              <div className="flex items-center gap-2 rounded-full border border-line bg-card px-4 py-1.5 transition-colors focus-within:border-foreground/30">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={loading ? "The clerk is thinking…" : "Ask about any camera…"}
                  aria-label="Ask the clerk"
                  disabled={loading}
                  className="flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-faint disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  aria-label="Send message"
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-foreground text-background transition-all enabled:hover:scale-105 enabled:active:scale-95 disabled:opacity-30"
                >
                  <ArrowUpIcon size={15} weight="bold" />
                </button>
              </div>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
