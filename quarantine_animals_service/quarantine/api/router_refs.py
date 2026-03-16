from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from ..db import get_cursor
from ..common.errors import NotFoundError, ValidationError
from .deps import get_current_user

router = APIRouter()


@router.get("/species", summary="Список видов животных")
def list_species():
    with get_cursor() as cur:
        cur.execute(
            "SELECT species_id, name, code, has_age_categories, has_mass_bins FROM qa_species ORDER BY name"
        )
        return cur.fetchall()


@router.get("/directions", summary="Список направлений учёта")
def list_directions():
    with get_cursor() as cur:
        cur.execute("SELECT direction_id, name, code FROM qa_directions ORDER BY name")
        return cur.fetchall()


@router.get("/species/{species_code}/age-categories", summary="Возрастные категории для вида")
def list_age_categories(species_code: str):
    with get_cursor() as cur:
        cur.execute("SELECT species_id FROM qa_species WHERE code=%s", (species_code,))
        sp = cur.fetchone()
        if not sp:
            raise NotFoundError(f"Вид '{species_code}' не найден")
        cur.execute(
            "SELECT age_cat_id, name FROM qa_age_categories WHERE species_id=%s ORDER BY name",
            (sp["species_id"],),
        )
        return cur.fetchall()


@router.get("/species/{species_code}/mass-bins", summary="Весовые категории для вида")
def list_mass_bins(species_code: str):
    with get_cursor() as cur:
        cur.execute("SELECT species_id FROM qa_species WHERE code=%s", (species_code,))
        sp = cur.fetchone()
        if not sp:
            raise NotFoundError(f"Вид '{species_code}' не найден")
        cur.execute(
            "SELECT mass_bin_id, name FROM qa_mass_bins WHERE species_id=%s ORDER BY name",
            (sp["species_id"],),
        )
        return cur.fetchall()


@router.get("/groups", summary="Список групп")
def list_groups():
    with get_cursor() as cur:
        cur.execute(
            """SELECT g.group_id, g.name, d.code AS direction_code, s.code AS species_code
               FROM qa_groups g
               JOIN qa_directions d ON d.direction_id = g.direction_id
               LEFT JOIN qa_species s ON s.species_id = g.species_id
               ORDER BY g.name"""
        )
        return cur.fetchall()


@router.get("/cohorts", summary="Список когорт")
def list_cohorts(show_inactive: bool = False):
    """Список когорт. По умолчанию только активные; передайте show_inactive=true чтобы увидеть все."""
    with get_cursor() as cur:
        where = "" if show_inactive else "WHERE c.is_active = TRUE"
        cur.execute(
            f"""SELECT c.cohort_id, c.label, c.status_tag, c.is_active,
                      d.code AS direction_code, s.code AS species_code
               FROM qa_cohorts c
               JOIN qa_directions d ON d.direction_id = c.direction_id
               LEFT JOIN qa_species s ON s.species_id = c.species_id
               {where}
               ORDER BY c.label"""
        )
        return cur.fetchall()


class CohortCreate(BaseModel):
    label: str
    direction_code: str
    species_code: Optional[str] = None
    status_tag: Optional[str] = None


@router.post("/cohorts", summary="Создать когорту")
def create_cohort(body: CohortCreate, user: str = Depends(get_current_user)):
    """Создать новую когорту животных.

    - `label` — уникальное обозначение (например, 'G2026-01')
    - `direction_code` — subsidiary | vivarium
    - `species_code` — опционально, если когорта для одного вида
    - `status_tag` — произвольная метка состояния
    """
    with get_cursor() as cur:
        cur.execute("SELECT direction_id FROM qa_directions WHERE code=%s", (body.direction_code,))
        direction = cur.fetchone()
        if not direction:
            raise ValidationError(f"Неизвестный direction_code: {body.direction_code}")

        species_id = None
        if body.species_code:
            cur.execute("SELECT species_id FROM qa_species WHERE code=%s", (body.species_code,))
            sp = cur.fetchone()
            if not sp:
                raise ValidationError(f"Неизвестный species_code: {body.species_code}")
            species_id = sp["species_id"]

        cur.execute(
            """INSERT INTO qa_cohorts (label, direction_id, species_id, status_tag, is_active)
               VALUES (%s, %s, %s, %s, TRUE)
               RETURNING cohort_id""",
            (body.label, direction["direction_id"], species_id, body.status_tag),
        )
        cohort_id = cur.fetchone()["cohort_id"]
    return {"ok": True, "cohort_id": cohort_id}


@router.patch("/cohorts/{cohort_id}/deactivate", summary="Деактивировать когорту")
def deactivate_cohort(cohort_id: int, user: str = Depends(get_current_user)):
    """Деактивировать когорту (is_active = false).

    Деактивированная когорта не отображается в активных списках,
    но сохраняется в истории операций.
    """
    with get_cursor() as cur:
        cur.execute("SELECT cohort_id, is_active FROM qa_cohorts WHERE cohort_id=%s", (cohort_id,))
        row = cur.fetchone()
        if not row:
            raise NotFoundError(f"Когорта {cohort_id} не найдена")
        if not row["is_active"]:
            raise ValidationError("Когорта уже деактивирована")
        cur.execute("UPDATE qa_cohorts SET is_active=FALSE WHERE cohort_id=%s", (cohort_id,))
    return {"ok": True, "message": f"Когорта {cohort_id} деактивирована"}
