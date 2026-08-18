import { NextRequest, NextResponse } from "next/server";
import { productImage, toSummary } from "@/data/catalog";
import { matchProducts, ToolCall } from "@/lib/match-products";

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://127.0.0.1:8000";

export type ChatResponse = {
  answer: string;
  sources: string[];
  threadId: string;
  products: Array<ReturnType<typeof toSummary> & { image: string }>;
};

/** Conversation state lives in the agent, keyed by thread id — only the new message
 *  travels. A first turn omits the id and adopts whichever one the agent returns. */
export async function POST(req: NextRequest) {
  let message: string;
  let threadId: string | undefined;
  try {
    const body = await req.json();
    message = body.message;
    threadId = body.threadId ?? undefined;
    if (typeof message !== "string" || !message.trim()) throw new Error("empty");
  } catch {
    return NextResponse.json({ error: "message required" }, { status: 400 });
  }

  try {
    const res = await fetch(`${AGENT_API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: message, thread_id: threadId ?? null }),
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `The clerk is unavailable right now (agent returned ${res.status}).` },
        { status: 502 }
      );
    }
    const data: {
      answer: string;
      sources?: string[];
      thread_id?: string;
      tool_calls?: ToolCall[];
    } = await res.json();

    const products = matchProducts(data.answer, data.tool_calls ?? []).map((p) => ({
      ...toSummary(p),
      image: productImage(p.slug),
    }));

    const payload: ChatResponse = {
      answer: data.answer,
      sources: data.sources ?? [],
      threadId: data.thread_id ?? threadId ?? "",
      products,
    };
    return NextResponse.json(payload);
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "TimeoutError";
    return NextResponse.json(
      {
        error: timedOut
          ? "The clerk took too long to answer. Try a simpler question."
          : "Could not reach the clerk. Is the agent API running?",
      },
      { status: 502 }
    );
  }
}
