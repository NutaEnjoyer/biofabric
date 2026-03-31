"""Репозиторий комментариев ОКС."""
from typing import Optional
from psycopg.rows import dict_row


def list_comments(conn, object_id: int) -> list[dict]:
    sql = """
        SELECT * FROM oks_comments
        WHERE object_id = %s
        ORDER BY created_at DESC
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [object_id])
        return cur.fetchall()


def create_comment(conn, object_id: int, text: str, author_id: int, stage_id: Optional[int] = None) -> dict:
    sql = """
        INSERT INTO oks_comments (object_id, stage_id, author_id, text)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [object_id, stage_id, author_id or None, text])
        return cur.fetchone()
