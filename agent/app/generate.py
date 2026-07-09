"""Generation — the 'augment + generate' half of RAG (L03 naive pass).

retrieve (hybrid + rerank) -> build a grounded prompt -> Claude -> {answer, sources}.
Kept linear on purpose: this is the baseline the evals (L06-07) measure and the
logic L04 lifts into a LangGraph agent.
"""
from anthropic import Anthropic

from app.config import settings
from app.retrieval import hybrid_retrieve
from app.rerank import rerank

_client = Anthropic(api_key=settings.anthropic_api_key)  # key from .env via pydantic settings

SYSTEM = """You are a photography assistant. Answer the user's question using ONLY the \
context below. If the answer is not in the context, say you don't know — do not use outside \
knowledge or guess. Be concise. When a detail is camera-specific, name the camera."""


def _format_context(chunks: list[dict]) -> str:
    """Number each chunk and label it with its source file, so the model can ground answers."""
    return "\n\n".join(
        f"[{i}] (source: {c['source']})\n{c['content']}" for i, c in enumerate(chunks, 1)
    )


def answer(query: str, k: int = 5) -> dict:
    """Retrieve -> rerank -> generate a grounded answer with cited sources."""
    chunks = rerank(query, hybrid_retrieve(query), top_n=k)
    if not chunks:
        return {"answer": "I don't know — nothing relevant was found.", "sources": []}

    prompt = f"Context:\n{_format_context(chunks)}\n\nQuestion: {query}"
    resp = _client.messages.create(
        model=settings.generation_model,
        max_tokens=1024,
        thinking={"type": "disabled"},  # grounded extract-and-cite; no reasoning needed
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    sources = list(dict.fromkeys(c["source"] for c in chunks))  # dedup, keep order
    return {"answer": text, "sources": sources}
