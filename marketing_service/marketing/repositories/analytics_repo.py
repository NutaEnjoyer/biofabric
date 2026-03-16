"""Репозиторий аналитики.

Читает аналитические VIEW из v8_marketing.sql:
- v_mk_plan_summary       — число постов по дням/каналам/статусам
- v_mk_distribution_by_topic   — распределение по рубрикам
- v_mk_distribution_by_format  — распределение по форматам
- v_mk_distribution_by_channel — распределение по каналам
- v_mk_calendar_density   — насыщенность сетки по дням
- v_mk_upcoming_week_gaps — дни без контента на ближайшую неделю
"""
from __future__ import annotations
from sqlalchemy import text, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any


class AnalyticsRepo:
    def __init__(self) -> None:
        pass

    async def plan_summary(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Число постов по дням / каналам / статусам (v_mk_plan_summary)."""
        res = await db.execute(text("SELECT * FROM v_mk_plan_summary"))
        return [dict(r._mapping) for r in res]

    async def by_topic(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Распределение по рубрикам (v_mk_distribution_by_topic)."""
        res = await db.execute(text("SELECT * FROM v_mk_distribution_by_topic"))
        return [dict(r._mapping) for r in res]

    async def by_format(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Распределение по форматам контента (v_mk_distribution_by_format)."""
        res = await db.execute(text("SELECT * FROM v_mk_distribution_by_format"))
        return [dict(r._mapping) for r in res]

    async def by_channel(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Распределение по каналам публикации (v_mk_distribution_by_channel)."""
        res = await db.execute(text("SELECT * FROM v_mk_distribution_by_channel"))
        return [dict(r._mapping) for r in res]

    async def density(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Насыщенность сетки — сколько постов запланировано на каждый день (v_mk_calendar_density)."""
        res = await db.execute(text("SELECT * FROM v_mk_calendar_density"))
        return [dict(r._mapping) for r in res]

    async def gaps(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Дни ближайшей недели без контента по каналам (v_mk_upcoming_week_gaps).

        Возвращает пустой список, если на неделю всё заполнено."""
        res = await db.execute(text("SELECT * FROM v_mk_upcoming_week_gaps"))
        return [dict(r._mapping) for r in res]

    async def warnings(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Визуальные индикаторы «провалов» (ТЗ п.4.3).

        Агрегирует три типа предупреждений:
        - content_gap    — недостаточно контента на неделю
        - topic_skew     — перекос по рубрике (>60% постов одной рубрики)
        - no_approved    — нет утверждённых постов
        """
        result: list[dict[str, Any]] = []

        # 1. Пробелы в контенте (из существующего VIEW)
        gaps = await self.gaps(db)
        if gaps:
            result.append({
                "type": "content_gap",
                "level": "warning",
                "message": "Недостаточно контента на неделю",
                "details": gaps,
            })

        # 2. Перекос по рубрике — доля одной рубрики > 60%
        by_topic = await self.by_topic(db)
        if by_topic:
            total = sum(r.get("post_count", 0) for r in by_topic)
            if total > 0:
                for row in by_topic:
                    share = row.get("post_count", 0) / total
                    if share > 0.6:
                        result.append({
                            "type": "topic_skew",
                            "level": "warning",
                            "message": "Перекос по рубрике",
                            "details": {"topic": row.get("topic_name"), "share_pct": round(share * 100)},
                        })

        # 3. Нет утверждённых постов
        res = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM mk_posts WHERE status_code = 'approved'")
        )
        approved_cnt = res.scalar_one()
        if approved_cnt == 0:
            result.append({
                "type": "no_approved",
                "level": "warning",
                "message": "Нет утверждённых постов",
                "details": None,
            })

        return result
