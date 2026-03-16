import csv
from io import StringIO
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from ..db import get_cursor

router = APIRouter()


@router.get("/reports/monthly-summary", summary="Свод по месяцу (итоги/движение/корректировки)")
def monthly_summary(period_month: str = Query(..., description="YYYY-MM")):
    sql = """
    SELECT s.code AS species_code, d.code AS direction_code,
           SUM(CASE WHEN entry_type='intake'            THEN quantity ELSE 0 END) AS intake,
           SUM(CASE WHEN entry_type='withdrawal'        THEN quantity ELSE 0 END) AS withdrawal,
           SUM(CASE WHEN entry_type='issue_for_control' THEN quantity ELSE 0 END) AS issue_for_control,
           SUM(CASE WHEN entry_type='movement_in'       THEN quantity ELSE 0 END) AS movement_in,
           SUM(CASE WHEN entry_type='movement_out'      THEN quantity ELSE 0 END) AS movement_out,
           SUM(CASE WHEN entry_type='adjustment'        THEN quantity ELSE 0 END) AS adjustment,
           SUM(CASE WHEN entry_type IN ('intake','movement_in')
                     THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control')
                     THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END)
               AS closing_balance
    FROM qa_ledger l
    JOIN qa_species    s ON s.species_id   = l.species_id
    JOIN qa_directions d ON d.direction_id = l.direction_id
    WHERE to_char(l.entry_date, 'YYYY-MM') = %s
      AND l.status_code IN ('current', 'archived', 'in_process')
    GROUP BY s.code, d.code
    ORDER BY s.code, d.code
    """
    with get_cursor() as cur:
        cur.execute(sql, (period_month,))
        rows = cur.fetchall()
    return rows


@router.get("/reports/dashboard", summary="Панель сводки: итого, по направлениям, текущий vs прошлый месяц")
def dashboard(period_month: str = Query(..., description="YYYY-MM текущего периода")):
    """
    Возвращает общее поголовье, разбивку по направлениям и дельту к прошлому месяцу (↑↓).
    """
    sql_balance = """
    SELECT d.code AS direction_code,
           SUM(CASE WHEN entry_type IN ('intake','movement_in') THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END)
               AS balance
    FROM qa_ledger l
    JOIN qa_directions d ON d.direction_id = l.direction_id
    WHERE to_char(l.entry_date, 'YYYY-MM') <= %s
      AND l.status_code IN ('current', 'archived', 'in_process')
    GROUP BY d.code
    """
    sql_prev_month = """
    SELECT to_char(to_date(%s, 'YYYY-MM') - interval '1 month', 'YYYY-MM') AS prev_month
    """
    with get_cursor() as cur:
        cur.execute(sql_prev_month, (period_month,))
        prev_month = cur.fetchone()["prev_month"]

        cur.execute(sql_balance, (period_month,))
        current_rows = cur.fetchall()

        cur.execute(sql_balance, (prev_month,))
        prev_rows = cur.fetchall()

    prev_map = {r["direction_code"]: r["balance"] or 0 for r in prev_rows}
    by_direction = []
    total_current = 0
    total_prev = 0
    for r in current_rows:
        cur_val = r["balance"] or 0
        prv_val = prev_map.get(r["direction_code"], 0)
        total_current += cur_val
        total_prev += prv_val
        by_direction.append({
            "direction_code": r["direction_code"],
            "current": cur_val,
            "prev": prv_val,
            "delta": cur_val - prv_val,
            "trend": "up" if cur_val > prv_val else ("down" if cur_val < prv_val else "same"),
        })

    return {
        "period_month": period_month,
        "prev_month": prev_month,
        "total": {
            "current": total_current,
            "prev": total_prev,
            "delta": total_current - total_prev,
            "trend": "up" if total_current > total_prev else ("down" if total_current < total_prev else "same"),
        },
        "by_direction": by_direction,
    }


@router.get("/reports/dynamics", summary="Динамика численности по месяцам")
def dynamics(
    from_month: str = Query(..., description="YYYY-MM начало"),
    to_month: str = Query(..., description="YYYY-MM конец"),
    group_by: str = Query("direction", description="direction | species | total"),
):
    if group_by == "direction":
        select_extra = ", d.code AS group_key"
        join_extra = "JOIN qa_directions d ON d.direction_id = l.direction_id"
        group_extra = ", d.code"
    elif group_by == "species":
        select_extra = ", s.code AS group_key"
        join_extra = "JOIN qa_species s ON s.species_id = l.species_id"
        group_extra = ", s.code"
    else:
        select_extra = ", 'total' AS group_key"
        join_extra = ""
        group_extra = ""

    sql = f"""
    SELECT to_char(l.entry_date, 'YYYY-MM') AS period_month{select_extra},
           SUM(CASE WHEN entry_type IN ('intake','movement_in') THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END)
               AS balance
    FROM qa_ledger l
    {join_extra}
    WHERE to_char(l.entry_date, 'YYYY-MM') BETWEEN %s AND %s
      AND l.status_code IN ('current', 'archived', 'in_process')
    GROUP BY to_char(l.entry_date, 'YYYY-MM'){group_extra}
    ORDER BY to_char(l.entry_date, 'YYYY-MM'){group_extra}
    """
    with get_cursor() as cur:
        cur.execute(sql, (from_month, to_month))
        rows = cur.fetchall()
    return rows


@router.get("/reports/history", summary="История операций (таймлайн) по виду и направлению")
def operations_history(
    species_code: str = Query(..., description="Код вида"),
    direction_code: str = Query(..., description="Код направления"),
    from_month: str = Query(None, description="YYYY-MM начало"),
    to_month: str = Query(None, description="YYYY-MM конец"),
):
    filters = [
        "s.code = %s",
        "d.code = %s",
        "l.status_code IN ('current','archived','in_process')",
    ]
    params: list = [species_code, direction_code]
    if from_month:
        filters.append("to_char(l.entry_date, 'YYYY-MM') >= %s")
        params.append(from_month)
    if to_month:
        filters.append("to_char(l.entry_date, 'YYYY-MM') <= %s")
        params.append(to_month)

    where = " AND ".join(filters)
    sql = f"""
    SELECT l.entry_id, l.entry_date, l.entry_type, l.status_code,
           l.quantity, l.sex, l.purpose_text, l.note,
           l.transfer_key,
           g.name  AS group_name,
           c.label AS cohort_label,
           l.created_at, l.created_by
    FROM qa_ledger l
    JOIN qa_species    s ON s.species_id   = l.species_id
    JOIN qa_directions d ON d.direction_id = l.direction_id
    LEFT JOIN qa_groups  g ON g.group_id  = l.group_id
    LEFT JOIN qa_cohorts c ON c.cohort_id = l.cohort_id
    WHERE {where}
    ORDER BY l.entry_date, l.entry_id
    """
    with get_cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return rows


@router.get("/reports/vivarium-groups", summary="Виварий: группы как визуальные блоки с поголовьем")
def vivarium_groups(period_month: str = Query(..., description="YYYY-MM")):
    sql = """
    SELECT g.group_id, g.name AS group_name,
           s.code AS species_code, s.name AS species_name,
           SUM(CASE WHEN entry_type IN ('intake','movement_in') THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END)
               AS balance
    FROM qa_ledger l
    JOIN qa_directions d ON d.direction_id = l.direction_id AND d.code = 'vivarium'
    JOIN qa_groups     g ON g.group_id     = l.group_id
    JOIN qa_species    s ON s.species_id   = l.species_id
    WHERE to_char(l.entry_date, 'YYYY-MM') <= %s
      AND l.status_code IN ('current', 'archived', 'in_process')
    GROUP BY g.group_id, g.name, s.code, s.name
    HAVING SUM(CASE WHEN entry_type IN ('intake','movement_in') THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END) > 0
    ORDER BY g.name, s.name
    """
    with get_cursor() as cur:
        cur.execute(sql, (period_month,))
        rows = cur.fetchall()

    groups: dict = {}
    for r in rows:
        gid = r["group_id"]
        if gid not in groups:
            groups[gid] = {
                "group_id": gid,
                "group_name": r["group_name"],
                "species": [],
            }
        groups[gid]["species"].append({
            "species_code": r["species_code"],
            "species_name": r["species_name"],
            "balance": r["balance"],
        })
    return list(groups.values())


@router.get("/export/csv", summary="Экспорт сводных данных за период в CSV")
def export_csv(period_month: str = Query(..., description="YYYY-MM")):
    sql = """
    SELECT s.code AS species_code, s.name AS species_name,
           d.code AS direction_code,
           SUM(CASE WHEN entry_type='intake'            THEN quantity ELSE 0 END) AS intake,
           SUM(CASE WHEN entry_type='withdrawal'        THEN quantity ELSE 0 END) AS withdrawal,
           SUM(CASE WHEN entry_type='issue_for_control' THEN quantity ELSE 0 END) AS issue_for_control,
           SUM(CASE WHEN entry_type='movement_in'       THEN quantity ELSE 0 END) AS movement_in,
           SUM(CASE WHEN entry_type='movement_out'      THEN quantity ELSE 0 END) AS movement_out,
           SUM(CASE WHEN entry_type='adjustment'        THEN quantity ELSE 0 END) AS adjustment,
           SUM(CASE WHEN entry_type IN ('intake','movement_in') THEN quantity ELSE 0 END)
           - SUM(CASE WHEN entry_type IN ('withdrawal','movement_out','issue_for_control') THEN quantity ELSE 0 END)
           + SUM(CASE WHEN entry_type='adjustment' THEN quantity ELSE 0 END)
               AS closing_balance
    FROM qa_ledger l
    JOIN qa_species    s ON s.species_id   = l.species_id
    JOIN qa_directions d ON d.direction_id = l.direction_id
    WHERE to_char(l.entry_date, 'YYYY-MM') = %s
      AND l.status_code IN ('current', 'archived', 'in_process')
    GROUP BY s.code, s.name, d.code
    ORDER BY s.name, d.code
    """
    with get_cursor() as cur:
        cur.execute(sql, (period_month,))
        rows = cur.fetchall()

    output = StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("no data")

    output.seek(0)
    filename = f"quarantine_{period_month}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
