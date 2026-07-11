"""LangGraph agent (L04): retrieve → grade → answer, with a query-rewrite loop.

DEPRECATED (L06): superseded by the main agent (app/agent.py), which we ship.
Its global (unfiltered) retrieval loses to the main agent's product-scoped search_manual
on per-camera questions (see evals/l06-ragas-baseline.md). Kept for reference/comparison only.

Same building blocks as the L03 pipeline (hybrid_retrieve, rerank, grounded prompt),
arranged as a StateGraph with one decision point: if retrieval looks weak,
rewrite the query and retry once.
"""
import warnings

from anthropic import Anthropic
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from app.config import settings
from app.retrieval import hybrid_retrieve
from app.rerank import rerank

_client = Anthropic(api_key=settings.anthropic_api_key)

TOP_N = 5
GRADE_THRESHOLD = 0.2  # top rerank score below this = retrieval found nothing relevant
MAX_ATTEMPTS = 1


class AgentState(TypedDict):
    query: str           # current search query — the rewrite node may replace it
    original_query: str  # what the user actually asked; the answer node uses this
    chunks: list[dict]   # retrieved + reranked: {content, source, score}
    answer: str
    sources: list[str]
    attempts: int        # rewrites so far; caps the retry loop at 1


def retrieve_node(state: AgentState) -> dict:
    chunks = rerank(state["query"], hybrid_retrieve(state["query"]), top_n=TOP_N)
    return {"chunks": chunks}


def grade(state: AgentState) -> str:
    """Conditional edge: decide where to go after retrieval."""
    top = state["chunks"][0]["score"] if state["chunks"] else 0.0
    if top >= GRADE_THRESHOLD or state["attempts"] >= MAX_ATTEMPTS:
        return "answer"
    return "rewrite"


def rewrite_node(state: AgentState) -> dict:
    """Rephrase the query for search. Only runs when grade says retrieval was weak."""
    resp = _client.messages.create(
        model=settings.generation_model,
        max_tokens=100,
        thinking={"type": "disabled"},
        system="Rewrite the user's photography question as a clear search query. "
               "Reply with the rewritten query only.",
        messages=[{"role": "user", "content": state["query"]}],
    )
    new_query = next((b.text for b in resp.content if b.type == "text"), state["query"])
    return {"query": new_query.strip(), "attempts": state["attempts"] + 1}


SYSTEM = """You are a photography assistant. Answer the user's question using ONLY the \
context below. If the answer is not in the context, say you don't know — do not use outside \
knowledge or guess. Be concise. When a detail is camera-specific, name the camera."""


def _format_context(chunks: list[dict]) -> str:
    """Number each chunk and label it with its source file, so the model can ground answers."""
    return "\n\n".join(
        f"[{i}] (source: {c['source']})\n{c['content']}" for i, c in enumerate(chunks, 1)
    )


def answer_node(state: AgentState) -> dict:
    if not state["chunks"]:
        return {"answer": "I don't know — nothing relevant was found.", "sources": []}

    prompt = f"Context:\n{_format_context(state['chunks'])}\n\nQuestion: {state['original_query']}"
    resp = _client.messages.create(
        model=settings.generation_model,
        max_tokens=1024,
        thinking={"type": "disabled"},  # grounded extract-and-cite; no reasoning needed
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    sources = list(dict.fromkeys(c["source"] for c in state["chunks"]))  # dedup, keep order
    return {"answer": text, "sources": sources}


graph = (
    StateGraph(AgentState)
    .add_node("retrieve", retrieve_node)
    .add_node("rewrite", rewrite_node)
    .add_node("answer", answer_node)
    .add_edge(START, "retrieve")
    .add_conditional_edges("retrieve", grade, ["answer", "rewrite"])
    .add_edge("rewrite", "retrieve")
    .add_edge("answer", END)
    .compile()
)


def ask(query: str) -> dict:
    """Run the agent and return {answer, sources, contexts}.

    contexts = the reranked chunk texts the answer node saw — needed by the
    eval harness (Ragas scores answers against retrieved contexts).
    """
    warnings.warn("app.manual_rag_agent is deprecated; use app.agent.", DeprecationWarning, stacklevel=2)
    final = graph.invoke({"query": query, "original_query": query, "attempts": 0})
    contexts = [c["content"] for c in final["chunks"]]
    return {
        "answer": final["answer"],
        "sources": final["sources"],
        "contexts": contexts,
        "retrieval_contexts": contexts,  # this agent has no routing tools — all context is retrieval
    }
