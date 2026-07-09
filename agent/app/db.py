"""Postgres/pgvector access. Thin helpers over psycopg 3."""
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector

from app.config import settings


@contextmanager
def get_conn():
    """Yield a connection with the pgvector type registered."""
    with psycopg.connect(settings.database_url) as conn:
        register_vector(conn)
        yield conn


def insert_chunks(source: str, rows: list[dict]) -> int:
    """Replace all chunks of a source: delete existing rows, bulk-insert the new ones.

    Rows: {source, content, token_count, embedding, doc_type, brand, product}.
    Delete-first makes ingest re-runnable without duplicating chunks — including
    when a source now produces zero chunks.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("delete from chunks where source = %s", (source,))
        cur.executemany(
            "insert into chunks (source, content, token_count, embedding, doc_type, brand, product) "
            "values (%(source)s, %(content)s, %(token_count)s, %(embedding)s, "
            "%(doc_type)s, %(brand)s, %(product)s)",
            rows,
        )
        conn.commit()
        return len(rows)
