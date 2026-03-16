"""Репозиторий источников.

- CRUD по mk_sources
- Получение «последних 10 материалов» из источника (заглушка; реальный парсинг вне БД)
"""
from __future__ import annotations
from sqlalchemy import Table, select, insert, delete, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional, List


class SourcesRepo:
    def __init__(self, metadata: MetaData) -> None:
        self.t_sources: Table = metadata.tables["mk_sources"]

    async def create(self, db: AsyncSession, name: str, url: str, kind: str | None) -> int:
        q = insert(self.t_sources).values(
            {"name": name, "url": url, "kind": kind, "approved": True}
        ).returning(self.t_sources.c.source_id)
        res = await db.execute(q)
        return res.scalar_one()

    async def list(self, db: AsyncSession) -> list[dict[str, Any]]:
        res = await db.execute(select(self.t_sources).order_by(self.t_sources.c.source_id.desc()))
        return [dict(r) for r in res.mappings().all()]

    async def delete(self, db: AsyncSession, source_id: int) -> None:
        await db.execute(delete(self.t_sources).where(self.t_sources.c.source_id == source_id))

    async def get_last_10(self, db: AsyncSession, source_id: int) -> list[dict[str, Any]]:
        """Заглушка для выборки «последних 10 материалов».

        В реальности мы считаем это задачей парсера/внешнего клиента (TG/RSS/URL),
        который вернёт нам перечень {title, url, summary}. Здесь вернём пустой список.
        """
        return []
