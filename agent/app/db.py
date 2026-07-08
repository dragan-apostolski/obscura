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


def insert_chunks(rows: list[dict]) -> int:
    """Bulk-insert chunk rows: {source, content, token_count, embedding}. Returns count."""
    if not rows:
        return 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(
            "insert into chunks (source, content, token_count, embedding) "
            "values (%(source)s, %(content)s, %(token_count)s, %(embedding)s)",
            rows,
        )
        conn.commit()
        return len(rows)
