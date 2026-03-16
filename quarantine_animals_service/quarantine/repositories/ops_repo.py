from typing import Optional, Dict, Any, List
from ..db import get_cursor
from ..common.errors import ValidationError, NotFoundError


def _fetch_one(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchone()


# ─── Lookups ────────────────────────────────────────────────────────────────

def _get_species_id(cur, code: str) -> Optional[int]:
    row = _fetch_one(cur, "SELECT species_id FROM qa_species WHERE code=%s", (code,))
    return row["species_id"] if row else None


def _get_direction_id(cur, code: str) -> Optional[int]:
    row = _fetch_one(cur, "SELECT direction_id FROM qa_directions WHERE code=%s", (code,))
    return row["direction_id"] if row else None


def _get_age_cat_id(cur, species_id: int, name: str) -> Optional[int]:
    row = _fetch_one(
        cur,
        "SELECT age_cat_id FROM qa_age_categories WHERE species_id=%s AND name=%s",
        (species_id, name),
    )
    return row["age_cat_id"] if row else None


def _get_mass_bin_id(cur, species_id: int, name: str) -> Optional[int]:
    row = _fetch_one(
        cur,
        "SELECT mass_bin_id FROM qa_mass_bins WHERE species_id=%s AND name=%s",
        (species_id, name),
    )
    return row["mass_bin_id"] if row else None


def _get_group_id(cur, group_id_or_name: str) -> Optional[int]:
    try:
        return int(group_id_or_name)
    except (ValueError, TypeError):
        row = _fetch_one(cur, "SELECT group_id FROM qa_groups WHERE name=%s", (group_id_or_name,))
        return row["group_id"] if row else None


def _get_cohort_id(cur, cohort_id_or_label: str) -> Optional[int]:
    try:
        return int(cohort_id_or_label)
    except (ValueError, TypeError):
        row = _fetch_one(cur, "SELECT cohort_id FROM qa_cohorts WHERE label=%s", (cohort_id_or_label,))
        return row["cohort_id"] if row else None


# ─── Validation ─────────────────────────────────────────────────────────────

def _validate_bins(cur, species_id: int, age_bin_code: Optional[str], mass_bin_code: Optional[str]):
    sp = _fetch_one(
        cur,
        "SELECT has_age_categories, has_mass_bins FROM qa_species WHERE species_id=%s",
        (species_id,),
    )
    if not sp:
        raise ValidationError("Вид не найден")
    if age_bin_code and not sp["has_age_categories"]:
        raise ValidationError("Для вида не предусмотрены возрастные категории")
    if mass_bin_code and not sp["has_mass_bins"]:
        raise ValidationError("Для вида не предусмотрены весовые категории")


def _resolve_refs(cur, d: Dict[str, Any]) -> Dict[str, Any]:
    species_id = _get_species_id(cur, d["species_code"])
    if not species_id:
        raise ValidationError("Неизвестный species_code")

    direction_id = _get_direction_id(cur, d["direction_code"])
    if not direction_id:
        raise ValidationError("Неизвестный direction_code")

    age_cat_id = None
    if d.get("age_bin_code"):
        age_cat_id = _get_age_cat_id(cur, species_id, d["age_bin_code"])
        if not age_cat_id:
            raise ValidationError("Неизвестный age_bin_code")

    mass_bin_id = None
    if d.get("mass_bin_code"):
        mass_bin_id = _get_mass_bin_id(cur, species_id, d["mass_bin_code"])
        if not mass_bin_id:
            raise ValidationError("Неизвестный mass_bin_code")

    def opt_group(key):
        val = d.get(key)
        if not val:
            return None
        gid = _get_group_id(cur, val)
        if not gid:
            raise ValidationError(f"Неизвестный {key}")
        return gid

    def opt_cohort(key):
        val = d.get(key)
        if not val:
            return None
        cid = _get_cohort_id(cur, val)
        if not cid:
            raise ValidationError(f"Неизвестный {key}")
        return cid

    return dict(
        species_id=species_id,
        direction_id=direction_id,
        age_cat_id=age_cat_id,
        mass_bin_id=mass_bin_id,
        group_id=opt_group("group_code"),
        cohort_id=opt_cohort("cohort_code"),
        src_group_id=opt_group("src_group_code"),
        src_cohort_id=opt_cohort("src_cohort_code"),
        dst_group_id=opt_group("dst_group_code"),
        dst_cohort_id=opt_cohort("dst_cohort_code"),
    )


# ─── Balance check ──────────────────────────────────────────────────────────

def _calc_balance(cur, d: dict) -> int:
    sql = """
    SELECT COALESCE(SUM(
        CASE entry_type
            WHEN 'intake'            THEN  quantity
            WHEN 'movement_in'       THEN  quantity
            WHEN 'withdrawal'        THEN -quantity
            WHEN 'issue_for_control' THEN -quantity
            WHEN 'movement_out'      THEN -quantity
            WHEN 'adjustment'        THEN  quantity
        END
    ), 0) AS balance
    FROM qa_ledger
    WHERE status_code IN ('current', 'archived', 'in_process')
      AND species_id   = %(species_id)s
      AND direction_id = %(direction_id)s
      AND COALESCE(sex, '')         = COALESCE(%(sex)s, '')
      AND COALESCE(age_cat_id,  0)  = COALESCE(%(age_cat_id)s,  0)
      AND COALESCE(mass_bin_id, 0)  = COALESCE(%(mass_bin_id)s, 0)
      AND COALESCE(group_id,    0)  = COALESCE(%(group_id)s,    0)
      AND COALESCE(cohort_id,   0)  = COALESCE(%(cohort_id)s,   0)
    """
    cur.execute(sql, d)
    row = cur.fetchone()
    return row["balance"] if row else 0


# ─── Insert ─────────────────────────────────────────────────────────────────

def _insert_ledger(cur, rec: dict) -> int:
    keys = ", ".join(rec.keys())
    ph = ", ".join(["%s"] * len(rec))
    cur.execute(
        f"INSERT INTO qa_ledger ({keys}) VALUES ({ph}) RETURNING entry_id",
        tuple(rec.values()),
    )
    return cur.fetchone()["entry_id"]


# ─── Public API ─────────────────────────────────────────────────────────────

def create_operation(data: dict, created_by: str | None = None) -> List[int]:
    with get_cursor() as cur:
        refs = _resolve_refs(cur, data)
        _validate_bins(cur, refs["species_id"], data.get("age_bin_code"), data.get("mass_bin_code"))

        note_parts = []
        if data.get("reason"):
            note_parts.append(f"reason: {data['reason']}")
        if data.get("adjusts_period"):
            note_parts.append(f"adjusts_period: {data['adjusts_period']}")

        base = dict(
            entry_date=data["date"],
            entry_type=data["op_type"],
            status_code="in_process",
            species_id=refs["species_id"],
            direction_id=refs["direction_id"],
            quantity=data["quantity"],
            sex=data.get("sex"),
            age_cat_id=refs["age_cat_id"],
            mass_bin_id=refs["mass_bin_id"],
            purpose_text=data.get("purpose_text"),
            note="\n".join(note_parts) if note_parts else None,
            created_by=None,  # user is string, ledger expects BIGINT FK
        )

        created_ids: List[int] = []

        def ensure_not_negative(src: dict, delta: int):
            balance = _calc_balance(cur, src)
            if balance + delta < 0:
                raise ValidationError("Операция приведёт к отрицательному остатку")

        if data["op_type"] in ("intake", "withdrawal", "issue_for_control", "adjustment"):
            rec = base.copy()
            rec["group_id"] = refs["group_id"]
            rec["cohort_id"] = refs["cohort_id"]

            if data["op_type"] == "issue_for_control":
                if not data.get("purpose_text"):
                    raise ValidationError("Для issue_for_control обязателен purpose_text")
                ensure_not_negative(dict(
                    species_id=refs["species_id"], direction_id=refs["direction_id"],
                    sex=data.get("sex"), age_cat_id=refs["age_cat_id"],
                    mass_bin_id=refs["mass_bin_id"],
                    group_id=refs["group_id"], cohort_id=refs["cohort_id"],
                ), -data["quantity"])

            if data["op_type"] == "withdrawal":
                ensure_not_negative(dict(
                    species_id=refs["species_id"], direction_id=refs["direction_id"],
                    sex=data.get("sex"), age_cat_id=refs["age_cat_id"],
                    mass_bin_id=refs["mass_bin_id"],
                    group_id=refs["group_id"], cohort_id=refs["cohort_id"],
                ), -data["quantity"])

            if data["op_type"] == "adjustment" and not data.get("reason"):
                raise ValidationError("Для adjustment обязателен reason")

            new_id = _insert_ledger(cur, rec)
            created_ids.append(new_id)
            return created_ids

        if data["op_type"] == "movement":
            src_group_id = refs["src_group_id"]
            src_cohort_id = refs["src_cohort_id"]
            dst_group_id = refs["dst_group_id"]
            dst_cohort_id = refs["dst_cohort_id"]

            if (not src_group_id and not src_cohort_id) or (not dst_group_id and not dst_cohort_id):
                raise ValidationError("Перемещение требует src_* и dst_*")
            if (src_group_id, src_cohort_id) == (dst_group_id, dst_cohort_id):
                raise ValidationError("Источник и приёмник не могут совпадать")

            import uuid
            transfer_key = data.get("transfer_key") or str(uuid.uuid4())

            ensure_not_negative(dict(
                species_id=refs["species_id"], direction_id=refs["direction_id"],
                sex=data.get("sex"), age_cat_id=refs["age_cat_id"],
                mass_bin_id=refs["mass_bin_id"],
                group_id=src_group_id, cohort_id=src_cohort_id,
            ), -data["quantity"])

            out_rec = base.copy()
            out_rec.update(entry_type="movement_out", group_id=src_group_id,
                           cohort_id=src_cohort_id, transfer_key=transfer_key)
            in_rec = base.copy()
            in_rec.update(entry_type="movement_in", group_id=dst_group_id,
                          cohort_id=dst_cohort_id, transfer_key=transfer_key)

            out_id = _insert_ledger(cur, out_rec)
            in_id = _insert_ledger(cur, in_rec)
            created_ids.extend([out_id, in_id])
            return created_ids

        raise ValidationError("Неподдерживаемый op_type")


def confirm_operation(entry_id: int, approved_by: str) -> None:
    with get_cursor() as cur:
        row = _fetch_one(cur, "SELECT entry_id, status_code FROM qa_ledger WHERE entry_id=%s", (entry_id,))
        if not row:
            raise NotFoundError("Запись не найдена")
        if row["status_code"] != "in_process":
            raise ValidationError(f"Нельзя подтвердить запись со статусом '{row['status_code']}'")
        cur.execute(
            "UPDATE qa_ledger SET status_code='current', note=COALESCE(note||E'\\n','')||%s WHERE entry_id=%s",
            (f"confirmed_by: {approved_by}", entry_id),
        )


def archive_operation(entry_id: int, archived_by: str) -> None:
    """Перевести запись из статуса 'current' в 'archived'.

    Архивируются записи прошедших периодов. Архивная запись
    не редактируется, но участвует в агрегатах отчётов.
    """
    with get_cursor() as cur:
        row = _fetch_one(cur, "SELECT entry_id, status_code FROM qa_ledger WHERE entry_id=%s", (entry_id,))
        if not row:
            raise NotFoundError("Запись не найдена")
        if row["status_code"] != "current":
            raise ValidationError(
                f"Архивировать можно только записи со статусом 'current', текущий: '{row['status_code']}'"
            )
        cur.execute(
            "UPDATE qa_ledger SET status_code='archived', note=COALESCE(note||E'\\n','')||%s WHERE entry_id=%s",
            (f"archived_by: {archived_by}", entry_id),
        )


def archive_month(period_month: str, archived_by: str) -> int:
    """Массово архивировать все 'current'-записи за указанный месяц.

    Возвращает количество заархивированных записей.
    """
    with get_cursor() as cur:
        cur.execute(
            """UPDATE qa_ledger
                  SET status_code = 'archived',
                      note = COALESCE(note||E'\\n','')||%s
                WHERE status_code = 'current'
                  AND to_char(entry_date, 'YYYY-MM') = %s""",
            (f"bulk_archived_by: {archived_by}", period_month),
        )
        return cur.rowcount
