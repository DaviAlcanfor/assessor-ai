import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from config.settings import settings


_pool = None


def _get_pool() -> pool.ThreadedConnectionPool:

    global _pool

    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.DATABASE_URI
        )

    return _pool


@contextmanager
def get_conn():

    conn = _get_pool().getconn()
    try:
        yield conn
    finally:
        _get_pool().putconn(conn)