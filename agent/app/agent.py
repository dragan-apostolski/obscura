"""The camera-store ReAct agent.

The model owns the control flow: it picks tools, reads results, and loops until it can
answer. Our leverage points are the tool docstrings and the system prompt below.

Conversation state lives in Postgres, keyed by `thread_id`, so a follow-up question
("does it come in black?") resolves against what was actually said rather than a
transcript replayed into the prompt. Callers that want a one-shot answer simply omit
`thread_id` and get a fresh thread.

Everything here is async. The checkpointer is async-only, and serving, streaming and the
eval sweep all share one agent instance rather than maintaining a sync twin.
"""
import asyncio
import re
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from langchain.agents import create_agent
from langchain.agents.middleware import ContextEditingMiddleware
from langchain.agents.middleware.context_editing import ClearToolUsesEdit
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage
from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

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


SYSTEM_PROMPT = """You are the shop assistant of an online camera store. We sell camera
bodies from Canon, Sony, Nikon, Panasonic, OM System and Fujifilm. At this moment we are only selling camera bodies (new, not used),
and we are not selling lenses or accessories.

Answer length:
- Default to 2-4 sentences. Lead with the answer — no filler openers.
- Give a longer answer only if the user asks for detail, or the question
  genuinely needs steps/a list (e.g. a multi-step technique walkthrough).
- No filler, no repeating the question back, no closing offers to help further.

Routing:
- Each tool's description says when to use it. When unsure of a product's
  slug, resolve it with search_products before calling other tools.
- If a request doesn't clearly map to one product (e.g. "how do I change
  white balance?" without naming a camera), ask which camera the user
  means before calling product-specific tools.
- For comparisons, fetch each product's info separately, then compare.

Grounding:
- Base product facts (prices, stock, specs) and manual/technique answers on tool results.
- When you used a manual, mention the source.

Store facts:
- Prices are in EUR.
- Be helpful, like a knowledgeable store clerk.

When you can't help:
- No matching product, tool failure, or the manual doesn't cover it: say
  so plainly — don't guess or improvise.
- Question unrelated to the store or photography: politely decline and
  redirect to what you can help with."""


# ---------- lifecycle ----------

_agent = None
_checkpoint_pool: AsyncConnectionPool | None = None
_init_lock = asyncio.Lock()


async def _build_agent():
    """Open the checkpointer's pool, ensure its tables exist, and compile the agent."""
    global _checkpoint_pool
    pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.checkpoint_pool_max_size,
        # AsyncPostgresSaver requires both: it manages its own transactions and reads rows
        # by column name.
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=False,
    )
    try:
        await pool.open()
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()   # idempotent: creates the checkpoint tables if absent
    except Exception:
        await pool.close()           # don't strand a half-built pool on a retry
        raise
    _checkpoint_pool = pool

    model = ChatAnthropic(
        model=settings.generation_model,
        api_key=settings.anthropic_api_key,
        max_tokens=4096,
        timeout=settings.request_timeout,  # without this the SDK timeout is disabled → infinite hangs
        max_retries=2,
    )
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        # Persisted history is resent in full on every turn, tool results included. A
        # single manual search is ~2k tokens, so without this a long conversation grows
        # until it costs more than it's worth and eventually hits the context limit.
        # Older tool outputs are dropped first; the dialogue itself is kept.
        middleware=[
            ContextEditingMiddleware(
                edits=[ClearToolUsesEdit(
                    trigger=settings.context_edit_trigger_tokens,
                    keep=settings.context_edit_keep_tool_results,
                )]
            )
        ],
    )


async def get_agent():
    """The process-wide agent, built on first use. Concurrent callers wait on one build."""
    global _agent
    if _agent is None:
        async with _init_lock:
            if _agent is None:            # re-check: another task may have built it
                _agent = await _build_agent()
    return _agent


async def close_agent() -> None:
    """Release the checkpointer pool. Called on API shutdown; safe if never built.

    Takes the lock so a concurrent get_agent() can't rebuild against a pool that is
    about to close."""
    global _agent, _checkpoint_pool
    async with _init_lock:
        _agent = None
        if _checkpoint_pool is not None:
            await _checkpoint_pool.close()
            _checkpoint_pool = None


# ---------- tracing ----------

class _NoOpSpan:
    """Stand-in for a Langfuse span when tracing isn't configured — same .update()
    interface, does nothing."""
    def update(self, **kwargs):
        pass


@asynccontextmanager
async def _traced_span(name: str, tags: list[str], session_id: str | None = None):
    """Open a Langfuse root span, or a no-op stand-in if Langfuse isn't configured.
    Callers always get the same (span, callbacks, trace_id) shape either way, so they
    never need to branch on whether tracing is on.

    session_id groups every trace of one eval run under a single id, so runs can be
    told apart and compared in Langfuse — without it each run is just an undifferentiated
    batch of traces sharing the same tags."""
    if _langfuse is None:
        yield _NoOpSpan(), [], None
        return
    with _langfuse.start_as_current_observation(as_type="span", name=name) as root:
        with propagate_attributes(tags=tags, session_id=session_id):
            yield root, [_langfuse_handler], _langfuse.get_current_trace_id()


# ---------- reading the result ----------

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


def _final_text(messages: list) -> str:
    """The answer text — not always the last message. The model sometimes says
    everything alongside its tool call, then closes with an empty turn once the tool
    result adds nothing; taking messages[-1] blindly returns "" there."""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.text.strip():
            return m.text
    return ""


def _answer(messages: list) -> dict:
    """What a caller of the assistant gets: {answer, sources}. This is the API response."""
    return {"answer": _final_text(messages), "sources": _sources(messages)}


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
    readable summary instead of the raw message blob. prompt_version ties a metric
    change back to the prompt that produced it."""
    root.update(
        input={"query": query},
        output={"answer": _final_text(messages), "sources": _sources(messages)},
        metadata={
            "tool_calls": _trace(messages)["tool_calls"],
            "prompt_version": settings.prompt_version,
            "model": settings.generation_model,
        },
    )


# ---------- running ----------

def _config(thread_id: str | None, callbacks: list) -> tuple[dict, str]:
    """Build the invoke config. A missing thread_id means a one-shot question, which
    still needs its own thread so it can't read another conversation's history.

    Ids are server-issued UUID4s and callers may only echo one back. A thread id is a
    bearer token for a conversation — accepting client-invented ids would let anyone
    claim a short, guessable one and read or poison whatever lands there.
    """
    if thread_id is not None:
        try:
            uuid.UUID(thread_id, version=4)
        except ValueError:
            raise ValueError("thread_id must be a UUID4 issued by this API") from None
        return {"configurable": {"thread_id": thread_id}, "callbacks": callbacks}, thread_id
    tid = str(uuid.uuid4())
    return {"configurable": {"thread_id": tid}, "callbacks": callbacks}, tid


async def _invoke(query: str, thread_id: str | None) -> tuple[list, str | None, str]:
    """Run the agent once. Returns (messages, trace_id, thread_id) — trace_id is None
    when Langfuse isn't configured (no keys in .env). The thread_id comes back because
    a one-shot call is assigned one here, and the caller needs it to follow up."""
    agent = await get_agent()
    async with _traced_span("ask", ["store-agent"]) as (root, callbacks, trace_id):
        config, tid = _config(thread_id, callbacks)
        result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]}, config)
        messages = result["messages"]
        _stamp_trace(root, query, messages)
    return messages, trace_id, tid


async def ask(query: str, thread_id: str | None = None) -> dict:
    """Answer one question. Pass a stable thread_id to continue a conversation; omit it
    and the returned thread_id starts one."""
    messages, _, tid = await _invoke(query, thread_id)
    return {**_answer(messages), "thread_id": tid}


async def ask_traced(query: str, thread_id: str | None = None) -> dict:
    """Same run as ask(), plus the evaluation trace and Langfuse trace_id (None if
    Langfuse isn't configured). For evals, not the API."""
    messages, trace_id, _ = await _invoke(query, thread_id)
    return {**_answer(messages), **_trace(messages), "trace_id": trace_id}


async def astream(query: str, thread_id: str | None = None) -> AsyncIterator[dict]:
    """Yield the answer as it is produced, so a client can render it progressively
    instead of waiting out the whole tool loop.

    Events: {"type": "token", "text": ...} while the model writes the answer,
            {"type": "tool", "name": ...} when it starts a tool call,
            {"type": "done", "sources": [...], "thread_id": ...} at the end.
    Tool-call events exist because the loop can be slow and silent — knowing the agent
    is reading a manual is better than a spinner.
    """
    agent = await get_agent()
    async with _traced_span("ask", ["store-agent", "stream"]) as (root, callbacks, _):
        config, tid = _config(thread_id, callbacks)
        # Keyed by call id, not name: a comparison fetches two products and a follow-up
        # searches a second manual, and those are the slow turns worth narrating.
        # Streamed tool calls arrive as fragments, so early chunks carry an empty name.
        seen_calls: set[str] = set()
        async for chunk, _meta in agent.astream(
            {"messages": [{"role": "user", "content": query}]}, config, stream_mode="messages"
        ):
            for call in getattr(chunk, "tool_calls", None) or []:
                key = call.get("id") or call.get("name")
                if call.get("name") and key not in seen_calls:
                    seen_calls.add(key)
                    yield {"type": "tool", "name": call["name"]}
            if isinstance(chunk, AIMessage) and chunk.text:
                yield {"type": "token", "text": chunk.text}

        # The stream carries deltas, not the final state — read it back for sources.
        state = await agent.aget_state(config)
        messages = state.values.get("messages", [])
        _stamp_trace(root, query, messages)
        yield {"type": "done", "sources": _sources(messages), "thread_id": tid}


async def ask_batch(queries: list[str], max_concurrency: int = 3,
                    per_item_timeout: float = 150.0,
                    session_id: str | None = None) -> list[dict]:
    """Run questions concurrently, traced (this is the eval path). IO-bound on the
    model API, so bounded by a semaphore. Pass the run's stamp as session_id to group
    its traces in Langfuse.

    Each question gets its own thread — eval rows are independent, and sharing one
    would let an earlier answer contaminate a later row.
    Order preserved; a failed/timed-out run yields an error dict instead of aborting.
    Concurrency is kept low on purpose — too many parallel calls trip the API rate
    limit and the retry backoff ends up slower than sequential. per_item_timeout is a
    hard cap so one hung question (e.g. a stuck tool/DB call the API timeout misses)
    can't wedge the whole batch. Prints per-item progress for visibility."""
    agent = await get_agent()
    sem = asyncio.Semaphore(max_concurrency)
    results: list[dict] = [None] * len(queries)  # type: ignore[list-item]
    done = 0

    async def run_one(i: int, q: str):
        nonlocal done
        async with sem:
            try:
                async with _traced_span("ask", ["store-agent", "eval"],
                                        session_id=session_id) as (root, callbacks, trace_id):
                    config, _ = _config(None, callbacks)
                    r = await asyncio.wait_for(
                        agent.ainvoke({"messages": [{"role": "user", "content": q}]}, config),
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
