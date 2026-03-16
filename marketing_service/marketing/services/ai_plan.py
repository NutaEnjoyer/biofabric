"""ИИ-генерация плана от промта (без дат).

MVP-реализация:
- Здесь заглушка генерации: вместо реального LLM — формируем несколько постов на основании промта.
- В реальном коде подключим LLM и дадим управляемый промт.
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import MetaData
from typing import Any, List
from ..repositories.posts_repo import PostsRepo

class AIPlanService:
    def __init__(self, metadata: MetaData) -> None:
        self.repo = PostsRepo(metadata)

    async def generate_from_prompt(self, db: AsyncSession, prompt: str, channels: List[int] | None, formats: List[int] | None) -> list[int]:
        """Создаёт набор черновиков на основе текстового промта (без дат)."""
        # Заглушка: 3 поста из одного промта
        post_ids: list[int] = []
        for i in range(1, 4):
            data = {
                "channel_id": (channels or [1])[0],
                "format_id": (formats or [1])[0],
                "topic_id": 1,
                "direction_id": None,
                "title": f"Идея #{i}: {prompt[:40]}",
                "text": f"Черновик на основе промта: {prompt} (вариант {i})",
                "planned_for": None,
                "source_code": "ai_generated",
            }
            pid = await self.repo.create_draft_post(db, data)
            post_ids.append(pid)
        return post_ids
