"""Text → chunks.

Token-aware fixed-size chunks (~400 tokens, ~50 overlap) via tiktoken. Sizes come from
settings. PDF manuals with a usable table of contents get section-aware chunks instead —
see `chunk_document` in `app/ingest.py`.
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