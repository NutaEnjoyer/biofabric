"""Бизнес-логика постов.

Что делает:
- Проверяет права и валидирует поля по этапам.
- Управляет переводами статусов совместно с Workflow (ядро).
- Реализует «замену поста в плане» с безопасным переносом даты.
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import MetaData
from typing import Any
from ..repositories.posts_repo import PostsRepo


class PostsService:
    def __init__(self, metadata: MetaData) -> None:
        self.repo = PostsRepo(metadata)

    async def create_draft(self, db: AsyncSession, data: dict[str, Any]) -> int:
        """Создаёт черновик поста.

        Пояснение: используется при ручном создании поста или когда ИИ сгенерировал контент без даты."""
        return await self.repo.create_draft_post(db, data)

    async def get(self, db: AsyncSession, post_id: int) -> dict[str, Any] | None:
        """Возвращает полную карточку поста (мета + контент)."""
        return await self.repo.get_post(db, post_id)

    async def update(self, db: AsyncSession, post_id: int, data: dict[str, Any]) -> None:
        """Обновляет карточку поста (мета/контент).

        Использование: правки текста, смена канала/формата, назначение даты и т.п."""
        await self.repo.update_post(db, post_id, data)

    async def set_status(self, db: AsyncSession, post_id: int, status: str) -> None:
        """Проставляет статус посту: draft/in_review/approved/scheduled/published/archived."""
        await self.repo.set_status(db, post_id, status)

    async def set_date(self, db: AsyncSession, post_id: int, ymd: str) -> None:
        """Назначает дату публикации (без времени)."""
        await self.repo.set_date(db, post_id, ymd)

    async def set_external_url(self, db: AsyncSession, post_id: int, url: str) -> None:
        """Сохраняет ссылку на внешнюю публикацию (TG/VK)."""
        await self.repo.set_external_url(db, post_id, url)

    async def replace_post_in_plan(
        self, db: AsyncSession, date_ymd: str, post_id_to_remove: int, idea_post_id_to_use: int
    ) -> int:
        """Заменяет пост на дату `date_ymd` другой идеей.

        Алгоритм:
        1) Убираем дату у старого поста (он уезжает в корзину идей)
        2) Назначаем дату для выбранной идеи
        3) Возвращаем post_id, который теперь стоит на этой дате"""
        # Снимаем дату у первого
        await self.repo.set_date(db, post_id_to_remove, None)  # type: ignore
        # Ставим дату второму
        await self.repo.set_date(db, idea_post_id_to_use, date_ymd)
        return idea_post_id_to_use
