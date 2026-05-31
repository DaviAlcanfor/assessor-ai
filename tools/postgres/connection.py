import psycopg2
from psycopg2 import pool
from config.settings import DATABASE_URI
from contextlib import contextmanager

_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URI
)

@contextmanager
def get_conn():

    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)