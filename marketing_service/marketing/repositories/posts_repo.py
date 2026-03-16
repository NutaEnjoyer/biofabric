"""Репозиторий постов.

Что делает:
- Инкапсулирует доступ к таблицам `mk_posts`, `mk_post_contents` и связанным справочникам.
- Использует reflection, чтобы не дублировать DDL в коде и не «упасть» при дельтах.
- Даёт CRUD и выборки для календаря.
"""
from __future__ import annotations
from datetime import date as dt_date
from sqlalchemy import Table, select, insert, update, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional


class PostsRepo:
    def __init__(self, metadata: MetaData) -> None:
        self.t_posts: Table = metadata.tables["mk_posts"]
        self.t_contents: Table = metadata.tables["mk_post_contents"]

    async def create_draft_post(self, db: AsyncSession, data: dict[str, Any]) -> int:
        """Создаёт черновик поста и возвращает его post_id.

        Обязательно: channel_id, format_id, topic_id
        Опционально: direction_id, title, text, planned_for, audience, goals, tone, hashtags
        """
        # --- mk_posts (метаданные) ---
        q = insert(self.t_posts).values({
            "channel_id": data["channel_id"],
            "format_id": data["format_id"],
            "topic_id": data["topic_id"],
            "direction_id": data.get("direction_id"),
            "title": data.get("title"),
            "audience": data.get("audience"),
            "goals": data.get("goals"),
            "tone": data.get("tone"),
            "planned_for": data.get("planned_for"),
            "status_code": "draft",
            "source_code": data.get("source_code", "manual"),
            "external_url": None,
        }).returning(self.t_posts.c.post_id)
        res = await db.execute(q)
        post_id = res.scalar_one()

        # --- mk_post_contents (текст) ---
        # Колонка называется body_md (NOT NULL), title живёт только в mk_posts
        q2 = insert(self.t_contents).values({
            "post_id": post_id,
            "body_md": data.get("text") or "",   # <-- правильное имя колонки
            "hashtags": data.get("hashtags"),
        })
        await db.execute(q2)
        return post_id

    async def get_post(self, db: AsyncSession, post_id: int) -> Optional[dict[str, Any]]:
        """Возвращает пост + основной контент (title из mk_posts, body_md из mk_post_contents)."""
        p, c = self.t_posts, self.t_contents
        q = select(p, c).join(c, c.c.post_id == p.c.post_id).where(p.c.post_id == post_id)
        res = await db.execute(q)
        row = res.mappings().first()
        return dict(row) if row else None

    async def list_posts(
        self,
        db: AsyncSession,
        period_from: Optional[str] = None,
        period_to: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Список постов за период (по planned_for) или все, если период не задан."""
        p, c = self.t_posts, self.t_contents
        q = select(p, c).join(c, c.c.post_id == p.c.post_id)
        if period_from:
            q = q.where(p.c.planned_for >= dt_date.fromisoformat(period_from))
        if period_to:
            q = q.where(p.c.planned_for <= dt_date.fromisoformat(period_to))
        q = q.order_by(p.c.planned_for.nulls_last(), p.c.post_id.desc())
        res = await db.execute(q)
        return [dict(r) for r in res.mappings().all()]

    async def update_post(self, db: AsyncSession, post_id: int, data: dict[str, Any]) -> None:
        """Обновляет метаданные поста и/или контент."""
        p, c = self.t_posts, self.t_contents

        # Поля mk_posts (включая title, audience, goals, tone)
        meta_keys = {
            "channel_id", "format_id", "topic_id", "direction_id",
            "planned_for", "title", "audience", "goals", "tone",
        }
        meta_fields = {k: v for k, v in data.items() if k in meta_keys and v is not None}
        if meta_fields:
            await db.execute(update(p).where(p.c.post_id == post_id).values(**meta_fields))

        # Поля mk_post_contents
        content_fields: dict[str, Any] = {}
        if "text" in data:
            content_fields["body_md"] = data["text"]   # <-- правильное имя колонки
        if "hashtags" in data:
            content_fields["hashtags"] = data["hashtags"]
        if content_fields:
            await db.execute(update(c).where(c.c.post_id == post_id).values(**content_fields))

    async def set_status(self, db: AsyncSession, post_id: int, status: str) -> None:
        """Проставляет статус посту (draft/in_review/approved/scheduled/published/archived)."""
        p = self.t_posts
        await db.execute(
            update(p).where(p.c.post_id == post_id).values(status_code=status)  # <-- правильное имя колонки
        )

    async def set_date(self, db: AsyncSession, post_id: int, ymd: str) -> None:
        """Назначает дату публикации (без времени)."""
        p = self.t_posts
        await db.execute(update(p).where(p.c.post_id == post_id).values(planned_for=ymd))

    async def set_external_url(self, db: AsyncSession, post_id: int, url: str) -> None:
        """Сохраняет ссылку на опубликованный пост в площадке."""
        p = self.t_posts
        await db.execute(update(p).where(p.c.post_id == post_id).values(external_url=url))
