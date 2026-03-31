import psycopg
from contextlib import contextmanager
from oks.config import DATABASE_URL


@contextmanager
def get_conn(autocommit: bool = True):
    conn = psycopg.connect(DATABASE_URL, autocommit=autocommit)
    try:
        yield conn
    finally:
        conn.close()
