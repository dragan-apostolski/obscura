"""L05 — the camera-store ReAct agent.

Unlike the L04 graph (hand-wired routing), here the model owns the control flow:
it picks tools, reads results, and loops until it can answer. Our leverage points
are the tool docstrings and this system prompt.
"""
import re

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage

from app.config import settings
from app.tools import TOOLS

SYSTEM_PROMPT = """You are the shop assistant of an online camera store. We sell camera
bodies from Canon, Sony, Nikon, Panasonic and OM System. At this moment we are only selling camera bodies (new, not used), 
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
)

store_agent = create_agent(model=_model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


def _sources(messages: list) -> list[str]:
    """Collect manual/guide sources cited in tool results, order kept."""
    seen: list[str] = []
    for m in messages:
        if isinstance(m, ToolMessage):
            for src in re.findall(r"\[source: ([^\]]+)\]", str(m.content)):
                if src not in seen:
                    seen.append(src)
    return seen


def ask_store(query: str) -> dict:
    """Run the store agent on one question. Same contract as L04: {answer, sources}."""
    result = store_agent.invoke({"messages": [{"role": "user", "content": query}]})
    messages = result["messages"]
    return {"answer": messages[-1].text, "sources": _sources(messages)}
