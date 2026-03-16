"""Репозиторий календаря и «корзины идей».

- Отдаёт простую раскладку «когда и что публиковать» по датам
- Отдаёт список постов без даты (идеи)
"""
from __future__ import annotations
from datetime import date as dt_date
from sqlalchemy import Table, select, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional


class CalendarRepo:
    def __init__(self, metadata: MetaData) -> None:
        self.t_posts: Table = metadata.tables["mk_posts"]
        self.t_contents: Table = metadata.tables["mk_post_contents"]

    async def calendar(
        self, db: AsyncSession, period_from: Optional[str], period_to: Optional[str]
    ) -> list[dict[str, Any]]:
        p, c = self.t_posts, self.t_contents
        q = select(p, c).join(c, c.c.post_id == p.c.post_id).where(p.c.planned_for.isnot(None))
        if period_from:
            q = q.where(p.c.planned_for >= dt_date.fromisoformat(period_from))
        if period_to:
            q = q.where(p.c.planned_for <= dt_date.fromisoformat(period_to))
        q = q.order_by(p.c.planned_for, p.c.post_id)
        res = await db.execute(q)
        return [dict(r) for r in res.mappings().all()]

    async def ideas_bucket(self, db: AsyncSession) -> list[dict[str, Any]]:
        p, c = self.t_posts, self.t_contents
        q = (
            select(p, c)
            .join(c, c.c.post_id == p.c.post_id)
            .where(p.c.planned_for.is_(None))
            .order_by(p.c.post_id.desc())
        )
        res = await db.execute(q)
        return [dict(r) for r in res.mappings().all()]
