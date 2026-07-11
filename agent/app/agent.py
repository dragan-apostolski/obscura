"""The main agent — a camera-store ReAct agent (L05, now the shipped agent).

Unlike the deprecated manual_rag graph (hand-wired routing), here the model owns the
control flow: it picks tools, reads results, and loops until it can answer. Our leverage
points are the tool docstrings and this system prompt.
"""
import asyncio
import re

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage

from app.config import settings
from app.tools import TOOLS

SYSTEM_PROMPT = """You are the shop assistant of an online camera store. We sell camera
bodies from Canon, Sony, Nikon, Panasonic, OM System and Fujifilm. At this moment we are only selling camera bodies (new, not used), 
and we are not selling lenses or accessories. 

Routing:
- Each tool's description says when to use it. When unsure of a product's
  slug, resolve it with search_products before calling other tools.
- If a request doesn't clearly map to one product (e.g. "how do I change
  white balance?" without naming a camera), ask which camera the user
  means before calling product-specific tools.
- For comparisons, fetch each product's info separately, then compare.

Answers:
- Base product facts (prices, stock, specs) and manual/technique answers
  on tool results; if the tools don't have the answer, say you don't know.
- When you used a manual, mention the source.
- Prices are in EUR. Be concise and helpful, like a knowledgeable store
  clerk. Politely decline questions unrelated to the store or photography."""


_model = ChatAnthropic(
    model=settings.generation_model,
    api_key=settings.anthropic_api_key,
    max_tokens=4096,
    timeout=settings.request_timeout,  # without this the SDK timeout is disabled → infinite hangs
    max_retries=2,
)

agent = create_agent(model=_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


def _sources(messages: list) -> list[str]:
    """Collect manual/guide sources cited in tool results, order kept."""
    seen: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            for src in re.findall(r"\[source: ([^\]]+)\]", str(m.content)):
                if src not in seen:
                    seen.append(src)
    return seen


# Tools whose output is evidence an answer should be grounded in. search_products is
# pure routing/browse (many rows, never the answer content itself) and is excluded;
# get_product_info returns the actual facts (price, specs) an answer should cite, so
# it counts as retrieval alongside the manual/technique search tools.
RETRIEVAL_TOOLS = {"search_manual", "explain_technique", "get_product_info"}


def _result(messages: list) -> dict:
    """Shape agent messages into the eval contract:
    {answer, sources, contexts, retrieval_contexts, tool_calls}.

    contexts = every tool's output, including search_products (used for behavioral
    asserts, which need the full trace). retrieval_contexts = only RETRIEVAL_TOOLS
    output — excludes search_products — used for Ragas.
    """
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    contexts = [str(m.content) for m in tool_messages]
    retrieval_contexts = [str(m.content) for m in tool_messages if m.name in RETRIEVAL_TOOLS]
    tool_calls = [
        {"name": tc["name"], "args": tc["args"]}
        for m in messages
        for tc in getattr(m, "tool_calls", None) or []
    ]
    return {
        "answer": messages[-1].text,
        "sources": _sources(messages),
        "contexts": contexts,
        "retrieval_contexts": retrieval_contexts,
        "tool_calls": tool_calls,
    }


def ask(query: str) -> dict:
    """Run the agent on one question."""
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    return _result(result["messages"])


async def ask_batch(queries: list[str], max_concurrency: int = 3,
                    per_item_timeout: float = 150.0) -> list[dict]:
    """Run questions concurrently (IO-bound on the model API), bounded by a semaphore.
    Order preserved; a failed/timed-out run yields an error dict instead of aborting.
    Concurrency is kept low on purpose — too many parallel calls trip the API rate
    limit and the retry backoff ends up slower than sequential. per_item_timeout is a
    hard cap so one hung question (e.g. a stuck tool/DB call the API timeout misses)
    can't wedge the whole batch. Prints per-item progress for visibility."""
    sem = asyncio.Semaphore(max_concurrency)
    results: list[dict] = [None] * len(queries)  # type: ignore[list-item]
    done = 0

    async def run_one(i: int, q: str):
        nonlocal done
        async with sem:
            try:
                r = await asyncio.wait_for(
                    agent.ainvoke({"messages": [{"role": "user", "content": q}]}),
                    timeout=per_item_timeout,
                )
                results[i] = _result(r["messages"])
            except Exception as e:
                results[i] = {"answer": f"(agent error: {type(e).__name__}: {e})",
                              "sources": [], "contexts": [], "retrieval_contexts": [],
                              "tool_calls": []}
        done += 1
        print(f"  [{done}/{len(queries)}] {q[:50]}", flush=True)

    await asyncio.gather(*(run_one(i, q) for i, q in enumerate(queries)))
    return results
