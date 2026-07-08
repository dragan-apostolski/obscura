"""Reranking. A cross-encoder re-scores retrieved chunks by reading each
(query, chunk) pair together — sharper than the bi-encoder embeddings, but only
run on a small candidate pool.
"""
from sentence_transformers import CrossEncoder

from app.config import settings

_model = CrossEncoder(settings.reranker_model)


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """Re-score `chunks` against `query` and return the top_n, best first."""
    if not chunks:
        return []
    pairs = [(query, c["content"]) for c in chunks]
    scores = _model.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda cs: cs[1], reverse=True)
    return [{**c, "score": float(score)} for c, score in ranked[:top_n]]
