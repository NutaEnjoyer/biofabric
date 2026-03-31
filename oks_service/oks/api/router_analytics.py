"""Роутер: аналитика ОКС."""
from fastapi import APIRouter, Depends
from psycopg.rows import dict_row

from oks.api.deps import get_db, require, User

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/summary")
def summary(
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Сводка по объектам ОКС: статусы, просрочки, активность."""
    with db.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status_code = 'planned')     AS planned_count,
                COUNT(*) FILTER (WHERE status_code = 'in_progress') AS in_progress_count,
                COUNT(*) FILTER (WHERE status_code = 'suspended')   AS suspended_count,
                COUNT(*) FILTER (WHERE status_code = 'completed')   AS completed_count,
                COUNT(*) AS total_count
            FROM oks_objects
        """)
        objects_stats = cur.fetchone()

        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE NOT is_completed
                    AND planned_end IS NOT NULL
                    AND CURRENT_DATE > planned_end) AS overdue_stages_count,
                COUNT(*) FILTER (WHERE status_code = 'in_progress') AS active_stages_count,
                COUNT(*) AS total_stages_count
            FROM oks_stages
        """)
        stages_stats = cur.fetchone()

        cur.execute("""
            SELECT COUNT(*) AS stale_objects_count
            FROM oks_objects
            WHERE updated_at IS NOT NULL
              AND CURRENT_DATE - updated_at::date >= (
                  SELECT threshold_days FROM oks_notification_rules WHERE rule_code = 'stale_object'
              )
              AND status_code NOT IN ('completed', 'suspended')
        """)
        stale = cur.fetchone() or {}

    return {
        "objects": objects_stats,
        "stages": stages_stats,
        "stale_objects_count": stale.get("stale_objects_count", 0),
    }


@router.get("/analytics/overdue")
def overdue_stages(
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Просроченные этапы с информацией об объекте и ответственном."""
    with db.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                s.stage_id,
                s.object_id,
                o.name AS object_name,
                s.name AS stage_name,
                s.planned_end,
                CURRENT_DATE - s.planned_end AS days_overdue,
                s.stage_owner_user_id
            FROM oks_stages s
            JOIN oks_objects o ON o.object_id = s.object_id
            WHERE s.is_completed = false
              AND s.planned_end IS NOT NULL
              AND CURRENT_DATE > s.planned_end
            ORDER BY days_overdue DESC
        """)
        return cur.fetchall()


@router.get("/analytics/upcoming")
def upcoming_stages(
    db=Depends(get_db),
    _user: User = Depends(require("view_object")),
):
    """Этапы с приближающимся сроком (−10 и −5 дней)."""
    with db.cursor(row_factory=dict_row) as cur:
        cur.execute("""
            SELECT
                s.stage_id,
                s.object_id,
                o.name AS object_name,
                s.name AS stage_name,
                s.planned_end,
                s.planned_end - CURRENT_DATE AS days_left,
                s.stage_owner_user_id
            FROM oks_stages s
            JOIN oks_objects o ON o.object_id = s.object_id
            WHERE s.is_completed = false
              AND s.planned_end IS NOT NULL
              AND s.planned_end >= CURRENT_DATE
              AND s.planned_end - CURRENT_DATE <= 10
            ORDER BY s.planned_end
        """)
        return cur.fetchall()
