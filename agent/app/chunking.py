"""Text → chunks.  (L01 — you implement this in the lesson.)

Goal: token-aware fixed-size chunks (~400 tokens, ~50 overlap) using tiktoken.
Start fixed-size; we revisit semantic chunking in the evals lesson.
"""
import tiktoken

from app.config import settings

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def chunk_text(
    text: str,
    max_tokens: int = settings.chunk_tokens,
    overlap: int = settings.chunk_overlap,
) -> list[str]:

    tokens = _enc.encode(text)
    step = max_tokens - overlap
    chunks = []
    for start in range(0, len(tokens), step):
        window = tokens[start : start + max_tokens]
        chunk = _enc.decode(window).strip()
        if chunk:
            chunks.append(chunk)
    return chunks