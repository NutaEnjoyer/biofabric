from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import metadata
from ..api.deps import get_db
from ..schemas.dto_common import ResponseOk
from ..repositories.calendar_repo import CalendarRepo

router = APIRouter()


@router.get("/calendar", response_model=ResponseOk)
async def calendar(
    period_from: str | None = None,
    period_to: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Очень простой календарь: показывает «когда и что публиковать».

    Фильтрация по периоду (даты включительно)."""
    repo = CalendarRepo(metadata)
    rows = await repo.calendar(db, period_from, period_to)
    return ResponseOk(data=rows)


@router.get("/ideas", response_model=ResponseOk)
async def ideas_bucket(db: AsyncSession = Depends(get_db)):
    """«Корзина идей»: посты без даты (draft)."""
    repo = CalendarRepo(metadata)
    rows = await repo.ideas_bucket(db)
    return ResponseOk(data=rows)
