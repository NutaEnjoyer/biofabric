"""Репозиторий объектов ОКС."""
from typing import Optional
from psycopg.rows import dict_row


def list_objects(
    conn,
    *,
    parent_object_id: Optional[int] = None,
    flat: bool = False,
    status_code: Optional[str] = None,
    initiator_user_id: Optional[int] = None,
    search: Optional[str] = None,
) -> list[dict]:
    conditions = []
    params: list = []

    if not flat and parent_object_id is None:
        conditions.append("parent_object_id IS NULL")
    elif parent_object_id is not None:
        conditions.append("parent_object_id = %s")
        params.append(parent_object_id)

    if status_code:
        conditions.append("status_code = %s")
        params.append(status_code)
    if initiator_user_id:
        conditions.append("initiator_user_id = %s")
        params.append(initiator_user_id)
    if search:
        conditions.append("(name ILIKE %s OR code ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT o.*,
               (SELECT COUNT(*) FROM oks_objects c WHERE c.parent_object_id = o.object_id) AS children_count,
               (SELECT COUNT(*) FROM oks_stages  s WHERE s.object_id = o.object_id) AS stages_count
        FROM oks_objects o
        {where}
        ORDER BY o.created_at DESC
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_object(conn, object_id: int) -> Optional[dict]:
    sql = """
        SELECT o.*,
               (SELECT COUNT(*) FROM oks_objects c WHERE c.parent_object_id = o.object_id) AS children_count,
               (SELECT COUNT(*) FROM oks_stages  s WHERE s.object_id = o.object_id) AS stages_count
        FROM oks_objects o
        WHERE o.object_id = %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [object_id])
        return cur.fetchone()


def create_object(conn, data: dict) -> dict:
    fields = [k for k in data if data[k] is not None]
    placeholders = ", ".join(["%s"] * len(fields))
    cols = ", ".join(fields)
    sql = f"""
        INSERT INTO oks_objects ({cols}, updated_at)
        VALUES ({placeholders}, now())
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [data[f] for f in fields])
        row = cur.fetchone()
    row["children_count"] = 0
    row["stages_count"] = 0
    return row


def update_object(conn, object_id: int, data: dict) -> Optional[dict]:
    fields = [k for k in data if data[k] is not None]
    if not fields:
        return get_object(conn, object_id)
    set_clause = ", ".join([f"{f} = %s" for f in fields])
    sql = f"""
        UPDATE oks_objects
        SET {set_clause}, updated_at = now()
        WHERE object_id = %s
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [data[f] for f in fields] + [object_id])
        row = cur.fetchone()
    if row:
        counts = _get_counts(conn, object_id)
        row.update(counts)
    return row


def delete_object(conn, object_id: int):
    """Вернуть: True — удалён, False — есть дочерние, None — не найден."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT object_id FROM oks_objects WHERE object_id = %s", [object_id])
        if not cur.fetchone():
            return None
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM oks_objects WHERE parent_object_id = %s",
            [object_id],
        )
        if cur.fetchone()["cnt"] > 0:
            return False
        cur.execute("DELETE FROM oks_objects WHERE object_id = %s", [object_id])
        return True


def _get_counts(conn, object_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM oks_objects c WHERE c.parent_object_id = %s) AS children_count,
                (SELECT COUNT(*) FROM oks_stages  s WHERE s.object_id = %s) AS stages_count
            """,
            [object_id, object_id],
        )
        return cur.fetchone()
