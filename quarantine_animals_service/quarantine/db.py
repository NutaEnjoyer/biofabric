import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import DATABASE_URL

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@contextmanager
def get_cursor():
    conn = get_conn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()
