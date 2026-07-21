"""Retrieval.  (L02 — vector search; L03 — hybrid + rerank.)"""
import re

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


RRF_K = 60   # smoothing constant from the RRF paper; 60 is the standard default
POOL = 20    # candidates pulled from each arm before fusing


def _or_tsquery(query: str) -> str:
    """Build an OR tsquery from free text: 'white balance x100v' -> 'white | balance | x100v'."""
    return " | ".join(re.findall(r"\w+", query.lower()))


def hybrid_retrieve(query: str, k: int = 20, product: str | None = None,
                    doc_type: str | None = None) -> list[dict]:
    """Vector + keyword search, merged with Reciprocal Rank Fusion (RRF).

    `product` / `doc_type` restrict BOTH arms to a metadata slice, so filtered-out
    chunks never enter the candidate pool (L05: no wrong-camera leakage by construction).
    """
    embedding = embed_query(query)
    conds, cond_params = [], []
    if product is not None:
        conds.append("product = %s")
        cond_params.append(product)
    if doc_type is not None:
        conds.append("doc_type = %s")
        cond_params.append(doc_type)
    meta_filter = (" and " + " and ".join(conds)) if conds else ""
    sql = f"""
        with q as (
            select to_tsquery('english', %s) as tsq   -- match any word (OR); ranked by ts_rank_cd
        ),
        vec as (                                    -- arm 1: nearest by meaning
            select id, content, source,
                   row_number() over (order by embedding <=> %s::vector) as rank
            from chunks
            where true{meta_filter}
            order by embedding <=> %s::vector   -- repeat distance (not rank): keeps the `order by <=> limit` pattern HNSW needs
            limit %s
        ),
        kw as (                                     -- arm 2: best keyword matches
            select id, content, source,
                   row_number() over (order by ts_rank_cd(content_tsv, (select tsq from q)) desc) as rank
            from chunks
            where content_tsv @@ (select tsq from q){meta_filter}
            limit %s
        )
        select coalesce(vec.content, kw.content) as content,
               coalesce(vec.source,  kw.source)  as source,
               coalesce(1.0 / (%s + vec.rank), 0)      -- RRF: sum of 1/(k + position)
             + coalesce(1.0 / (%s + kw.rank), 0) as score
        from vec
        full outer join kw on vec.id = kw.id         -- keep chunks found by either arm
        order by score desc
        limit %s
    """
    params = (_or_tsquery(query), embedding, *cond_params, embedding, POOL,
              *cond_params, POOL, RRF_K, RRF_K, k)
    rows = _query_rows(sql, params)
    return [{"content": c, "source": s, "score": score} for c, s, score in rows]
