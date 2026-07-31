"""The main agent — a camera-store ReAct agent.

Unlike the deprecated manual_rag graph (hand-wired routing), here the model owns the
control flow: it picks tools, reads results, and loops until it can answer. Our leverage
points are the tool docstrings and this system prompt.
"""
import asyncio
import re
from contextlib import contextmanager

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage
from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

from app.config import settings
from app.tools import TOOLS

if settings.langfuse_public_key and settings.langfuse_secret_key:
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )
    _langfuse = get_client()
    _langfuse_handler = CallbackHandler()
else:
    _langfuse = None
    _langfuse_handler = None


class _NoOpSpan:
    """Stand-in for a Langfuse span when tracing isn't configured — same .update()
    interface, does nothing."""
    def update(self, **kwargs):
        pass


@contextmanager
def _traced_span(name: str, tags: list[str]):
    """Open a Langfuse root span, or a no-op stand-in if Langfuse isn't configured.
    Callers always get the same (span, callbacks, trace_id) shape either way, so they
    never need to branch on whether tracing is on."""
    if _langfuse is None:
        yield _NoOpSpan(), [], None
        return
    with _langfuse.start_as_current_observation(as_type="span", name=name) as root:
        with propagate_attributes(tags=tags):
            yield root, [_langfuse_handler], _langfuse.get_current_trace_id()


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


def _answer(messages: list) -> dict:
    """What a caller of the assistant gets: {answer, sources}. This is the API response."""
    return {"answer": messages[-1].text, "sources": _sources(messages)}


def _trace(messages: list) -> dict:
    """How the answer was produced — for evaluation, never for the API response.

    contexts            every successful tool call's output, one entry per call
    retrieval_contexts  evidence only (RETRIEVAL_TOOLS), one entry per chunk; a failed
                        search contributes nothing
    tool_calls          name + args of every call, in order
    """
    tool_messages = [m for m in messages if isinstance(m, ToolMessage) and m.status != "error"]
    return {
        "contexts": [str(m.content) for m in tool_messages],
        "retrieval_contexts": [
            chunk["content"]
            for m in tool_messages if m.name in RETRIEVAL_TOOLS
            for chunk in (m.artifact if m.artifact is not None
                          else [{"content": str(m.content)}])
        ],
        "tool_calls": [
            {"name": tc["name"], "args": tc["args"]}
            for m in messages
            for tc in getattr(m, "tool_calls", None) or []
        ],
    }


def _stamp_trace(root, query: str, messages: list) -> None:
    """Write the clean query/answer/sources onto the root span, so the trace shows a
    readable summary instead of the raw message blob."""
    root.update(
        input={"query": query},
        output={"answer": messages[-1].text, "sources": _sources(messages)},
        metadata={"tool_calls": _trace(messages)["tool_calls"]},
    )


def _invoke(query: str) -> tuple[list, str | None]:
    """Run the agent once. Returns (messages, trace_id) — trace_id is None when
    Langfuse isn't configured (no keys in .env)."""
    with _traced_span("ask", ["manual-rag-agent"]) as (root, callbacks, trace_id):
        messages = agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config={"callbacks": callbacks},
        )["messages"]
        _stamp_trace(root, query, messages)
    return messages, trace_id


def ask(query: str) -> dict:
    """Run the agent on one question."""
    messages, _ = _invoke(query)
    return _answer(messages)


def ask_traced(query: str) -> dict:
    """Same run as ask(), plus the evaluation trace and Langfuse trace_id (None if
    Langfuse isn't configured). For evals, not the API."""
    messages, trace_id = _invoke(query)
    return {**_answer(messages), **_trace(messages), "trace_id": trace_id}


async def ask_batch(queries: list[str], max_concurrency: int = 3,
                    per_item_timeout: float = 150.0) -> list[dict]:
    """Run questions concurrently, traced (this is the eval path). IO-bound on the
    model API, so bounded by a semaphore.
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
                with _traced_span("ask", ["manual-rag-agent", "eval"]) as (root, callbacks, trace_id):
                    r = await asyncio.wait_for(
                        agent.ainvoke(
                            {"messages": [{"role": "user", "content": q}]},
                            config={"callbacks": callbacks},
                        ),
                        timeout=per_item_timeout,
                    )
                    messages = r["messages"]
                    _stamp_trace(root, q, messages)
                results[i] = {**_answer(messages), **_trace(messages), "trace_id": trace_id}
            except Exception as e:
                results[i] = {"answer": f"(agent error: {type(e).__name__}: {e})",
                              "sources": [], "contexts": [], "retrieval_contexts": [],
                              "tool_calls": [], "trace_id": None}
        done += 1
        print(f"  [{done}/{len(queries)}] {q[:50]}", flush=True)

    await asyncio.gather(*(run_one(i, q) for i, q in enumerate(queries)))
    return results
