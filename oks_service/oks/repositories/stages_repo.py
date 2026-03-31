"""Репозиторий этапов ОКС."""
from datetime import date
from typing import Optional
from psycopg.rows import dict_row


def list_stages(conn, object_id: int) -> list[dict]:
    sql = """
        SELECT s.*,
               CASE WHEN s.is_completed THEN false
                    WHEN s.planned_end IS NOT NULL AND CURRENT_DATE > s.planned_end THEN true
                    ELSE false END AS is_overdue
        FROM oks_stages s
        WHERE s.object_id = %s
        ORDER BY s.parent_stage_id NULLS FIRST, s.created_at
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [object_id])
        return cur.fetchall()


def get_stage(conn, stage_id: int) -> Optional[dict]:
    sql = """
        SELECT s.*,
               CASE WHEN s.is_completed THEN false
                    WHEN s.planned_end IS NOT NULL AND CURRENT_DATE > s.planned_end THEN true
                    ELSE false END AS is_overdue
        FROM oks_stages s
        WHERE s.stage_id = %s
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [stage_id])
        return cur.fetchone()


def create_stage(conn, object_id: int, data: dict) -> dict:
    data = {k: v for k, v in data.items() if v is not None}
    data["object_id"] = object_id
    fields = list(data.keys())
    placeholders = ", ".join(["%s"] * len(fields))
    cols = ", ".join(fields)
    sql = f"""
        INSERT INTO oks_stages ({cols}, updated_at)
        VALUES ({placeholders}, now())
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [data[f] for f in fields])
        row = cur.fetchone()
    row["is_overdue"] = (
        not row["is_completed"]
        and row.get("planned_end") is not None
        and date.today() > row["planned_end"]
    )
    return row


def update_stage(conn, stage_id: int, data: dict) -> Optional[dict]:
    fields = [k for k in data if data[k] is not None]
    if not fields:
        return get_stage(conn, stage_id)
    set_clause = ", ".join([f"{f} = %s" for f in fields])
    sql = f"""
        UPDATE oks_stages
        SET {set_clause}, updated_at = now()
        WHERE stage_id = %s
        RETURNING *
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, [data[f] for f in fields] + [stage_id])
        row = cur.fetchone()
    if row:
        row["is_overdue"] = (
            not row["is_completed"]
            and row.get("planned_end") is not None
            and date.today() > row["planned_end"]
        )
    return row


def delete_stage(conn, stage_id: int) -> bool:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("DELETE FROM oks_stages WHERE stage_id = %s RETURNING stage_id", [stage_id])
        return cur.fetchone() is not None
