"""Postgres/pgvector access, over a psycopg 3 connection pool.

A single agent turn can make several tool calls, each hitting the database, so
connecting per query costs a TCP + TLS + auth round trip on the hot path. The pool is
opened lazily on first use — which keeps scripts like `app.ingest` working without any
setup — and the API closes it explicitly on shutdown.
"""
import threading
from contextlib import contextmanager

from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()
_closed = False


def get_pool() -> ConnectionPool:
    """The process-wide pool, created on first call.

    Guarded by a threading lock, not an asyncio one: tools run in the executor, so
    concurrent first calls arrive on different threads. Without it two pools get built
    and one is orphaned with its connections and worker threads still alive.
    """
    global _pool
    if _pool is None:
        with _pool_lock:
            if _closed:
                raise RuntimeError("connection pool is closed")
            if _pool is None:            # re-check: another thread may have built it
                _pool = ConnectionPool(
                    settings.database_url,
                    min_size=settings.db_pool_min_size,
                    max_size=settings.db_pool_max_size,
                    # runs once per physical connection, not per checkout
                    configure=register_vector,
                    open=True,
                )
    return _pool


def close_pool() -> None:
    """Close every pooled connection. Called on API shutdown; safe if never opened.

    Sets a closed flag rather than resetting to None, so a late request can't quietly
    reopen a pool while the process is shutting down.
    """
    global _pool, _closed
    with _pool_lock:
        _closed = True
        if _pool is not None:
            _pool.close()
            _pool = None


@contextmanager
def get_conn():
    """Borrow a connection from the pool. Committed on clean exit, rolled back on error."""
    with get_pool().connection() as conn:
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
        return len(rows)
