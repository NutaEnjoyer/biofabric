"""ИИ-идеи из импортированных материалов (по 10 с источника).

MVP-реализация:
- Импорт материалов делает внешний парсер (TG/RSS/URL), здесь — заглушка пустого списка.
- Из «сырья» генерируем черновики-идеи без дат.
- Дедупликация — внутри промта (не реализуем на уровне БД/кода в MVP).
"""
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import MetaData
from typing import Any, List
from ..repositories.posts_repo import PostsRepo
from ..repositories.sources_repo import SourcesRepo

class AISourcesService:
    def __init__(self, metadata: MetaData) -> None:
        self.posts = PostsRepo(metadata)
        self.sources = SourcesRepo(metadata)

    async def ideas_from_sources(self, db: AsyncSession, source_ids: List[int] | None, limit_per_source: int = 10) -> list[int]:
        """Генерирует черновики из материалов источников (без дат)."""
        created: list[int] = []
        # На MVP просто создадим N идей на источник без реального парсинга:
        ids = source_ids or []
        if not ids:
            # взять все источники
            all_src = await self.sources.list(db)
            ids = [s["source_id"] for s in all_src]
        for sid in ids:
            for i in range(1, min(limit_per_source, 10) + 1):
                data = {
                    "channel_id": 1,
                    "format_id": 1,
                    "topic_id": 1,
                    "title": f"Идея из источника {sid} #{i}",
                    "text": f"Сгенерированный черновик на основе материала #{i} из источника {sid}.",
                    "planned_for": None,
                    "source_code": "ai_generated",
                }
                pid = await self.posts.create_draft_post(db, data)
                created.append(pid)
        return created
