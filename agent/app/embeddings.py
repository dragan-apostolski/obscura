"""Text → vectors. Local BAAI/bge-small-en-v1.5 (384-dim) — free + offline.

bge retrieval models want a short instruction prefix on *queries* (not on
documents/passages). So: embed passages raw (embed / embed_one); embed a
search query with embed_query(). Vectors are L2-normalized so pgvector's
cosine distance behaves well.

The model is loaded on first use rather than at import, so importing this module stays
cheap and the load happens where it can be controlled — see `warmup()`.
"""
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None

# Prepended to search queries only (bge convention) — improves retrieval.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def warmup() -> None:
    """Load the model now. Called at API startup so the first request doesn't pay for it."""
    _get_model()


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of passages (documents). One 384-dim vector per input."""
    return _get_model().encode(texts, normalize_embeddings=True).tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def embed_query(text: str) -> list[float]:
    """Embed a search query, with the bge retrieval prefix. Use this in retrieve()."""
    return _get_model().encode([_QUERY_PREFIX + text], normalize_embeddings=True)[0].tolist()
