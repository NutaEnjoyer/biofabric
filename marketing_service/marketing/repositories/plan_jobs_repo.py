"""Репозиторий задач генерации контент-плана (mk_plan_jobs).

ТЗ п.1, п.5: «Постановка задач на генерацию контент-планов по направлениям»,
«Указание целевой аудитории, целей публикаций и желаемого стиля».
"""
from __future__ import annotations
from sqlalchemy import Table, select, insert, update, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional


class PlanJobsRepo:
    def __init__(self, metadata: MetaData) -> None:
        self.t: Table = metadata.tables["mk_plan_jobs"]

    async def create(self, db: AsyncSession, data: dict[str, Any]) -> int:
        """Создаёт задачу генерации контент-плана, статус 'pending'."""
        q = insert(self.t).values({
            "period_start": data["period_start"],
            "period_end": data["period_end"],
            "direction_id": data.get("direction_id"),
            "audience": data.get("audience"),
            "goals": data.get("goals"),
            "tone": data.get("tone"),
            "status": "pending",
            "created_by": data.get("created_by"),
        }).returning(self.t.c.job_id)
        res = await db.execute(q)
        return res.scalar_one()

    async def get(self, db: AsyncSession, job_id: int) -> Optional[dict[str, Any]]:
        """Возвращает задачу по ID."""
        res = await db.execute(select(self.t).where(self.t.c.job_id == job_id))
        row = res.mappings().first()
        return dict(row) if row else None

    async def list(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Список всех задач (новые сверху)."""
        res = await db.execute(select(self.t).order_by(self.t.c.job_id.desc()))
        return [dict(r) for r in res.mappings().all()]

    async def set_status(self, db: AsyncSession, job_id: int, status: str) -> None:
        """Обновляет статус задачи (running / done / failed)."""
        await db.execute(update(self.t).where(self.t.c.job_id == job_id).values(status=status))
