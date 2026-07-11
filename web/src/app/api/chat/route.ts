import { NextRequest, NextResponse } from "next/server";
import { productImage, toSummary } from "@/data/catalog";
import { matchProducts, ToolCall } from "@/lib/match-products";

const AGENT_API_URL = process.env.AGENT_API_URL ?? "http://127.0.0.1:8000";

export type ChatTurn = { role: "user" | "assistant"; content: string };

export type ChatResponse = {
  answer: string;
  sources: string[];
  products: Array<ReturnType<typeof toSummary> & { image: string }>;
};

/** The FastAPI agent takes a single query string, so multi-turn context is
 *  folded into the prompt as a transcript. */
function buildQuery(messages: ChatTurn[]): string {
  const last = messages[messages.length - 1];
  if (messages.length === 1) return last.content;
  const history = messages
    .slice(0, -1)
    .map((m) => `${m.role === "user" ? "Customer" : "You (clerk)"}: ${m.content}`)
    .join("\n");
  return `Earlier in this conversation:\n${history}\n\nThe customer now asks: ${last.content}`;
}

export async function POST(req: NextRequest) {
  let messages: ChatTurn[];
  try {
    const body = await req.json();
    messages = body.messages;
    if (!Array.isArray(messages) || messages.length === 0) throw new Error("empty");
  } catch {
    return NextResponse.json({ error: "messages array required" }, { status: 400 });
  }

  try {
    const res = await fetch(`${AGENT_API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: buildQuery(messages) }),
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) {
      return NextResponse.json(
        { error: `The clerk is unavailable right now (agent returned ${res.status}).` },
        { status: 502 }
      );
    }
    const data: { answer: string; sources?: string[]; tool_calls?: ToolCall[] } =
      await res.json();

    const products = matchProducts(data.answer, data.tool_calls ?? []).map((p) => ({
      ...toSummary(p),
      image: productImage(p.slug),
    }));

    const payload: ChatResponse = {
      answer: data.answer,
      sources: data.sources ?? [],
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
