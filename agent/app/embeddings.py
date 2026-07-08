"""Text → vectors. Local BAAI/bge-small-en-v1.5 (384-dim) — free + offline.

bge retrieval models want a short instruction prefix on *queries* (not on
documents/passages). So: embed passages raw (embed / embed_one); embed a
search query with embed_query(). Vectors are L2-normalized so pgvector's
cosine distance behaves well.
"""
from sentence_transformers import SentenceTransformer

from app.config import settings

_model = SentenceTransformer(settings.embedding_model)

# Prepended to search queries only (bge convention) — improves retrieval.
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of passages (documents). One 384-dim vector per input."""
    return _model.encode(texts, normalize_embeddings=True).tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]


def embed_query(text: str) -> list[float]:
    """Embed a search query, with the bge retrieval prefix. Use this in retrieve()."""
    return _model.encode([_QUERY_PREFIX + text], normalize_embeddings=True)[0].tolist()
