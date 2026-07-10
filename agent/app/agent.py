"""The main agent — a camera-store ReAct agent (L05, now the shipped agent).

Unlike the deprecated manual_rag graph (hand-wired routing), here the model owns the
control flow: it picks tools, reads results, and loops until it can answer. Our leverage
points are the tool docstrings and this system prompt.
"""
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


def _result(messages: list) -> dict:
    """Shape agent messages into the eval contract: {answer, sources, contexts, tool_calls}."""
    contexts = [str(m.content) for m in messages if isinstance(m, ToolMessage)]
    tool_calls = [
        {"name": tc["name"], "args": tc["args"]}
        for m in messages
        for tc in getattr(m, "tool_calls", None) or []
    ]
    return {
        "answer": messages[-1].text,
        "sources": _sources(messages),
        "contexts": contexts,
        "tool_calls": tool_calls,
    }


def ask(query: str) -> dict:
    """Run the agent on one question."""
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})
    return _result(result["messages"])


async def ask_batch(queries: list[str], max_concurrency: int = 5) -> list[dict]:
    """Run many questions concurrently (IO-bound on the model API). Order preserved;
    a failed/timed-out run yields an error dict instead of aborting the batch."""
    inputs = [{"messages": [{"role": "user", "content": q}]} for q in queries]
    results = await agent.abatch(
        inputs, config={"max_concurrency": max_concurrency}, return_exceptions=True
    )
    out = []
    for r in results:
        if isinstance(r, Exception):
            out.append({"answer": f"(agent error: {type(r).__name__}: {r})",
                        "sources": [], "contexts": [], "tool_calls": []})
        else:
            out.append(_result(r["messages"]))
    return out
