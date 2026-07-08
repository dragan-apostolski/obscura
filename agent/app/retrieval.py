"""Retrieval.  (L02 — vector search; L03 — hybrid + rerank.)"""
from app.db import get_conn
from app.embeddings import embed_query


def _query_rows(sql: str, params: tuple) -> list[tuple]:
    """Run a read query and return all rows."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def retrieve(query: str, k: int = 5) -> list[dict]:
    """Return the k most similar chunks to `query` (<=> is cosine distance)."""
    embedding = embed_query(query)
    sql = """
        select content, source, 1 - (embedding <=> %s::vector) as score
        from chunks
        order by embedding <=> %s::vector
        limit %s
    """
    rows = _query_rows(sql, (embedding, embedding, k))
    return [{"content": c, "source": s, "score": score} for c, s, score in rows]
