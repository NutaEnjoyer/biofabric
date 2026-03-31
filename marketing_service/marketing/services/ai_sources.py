"""ИИ-идеи из источников (по N идей на источник)."""
from __future__ import annotations
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import MetaData
from typing import List
from openai import AsyncOpenAI
from ..repositories.posts_repo import PostsRepo
from ..repositories.sources_repo import SourcesRepo
from ..config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Ты — контент-менеджер биофабрики. "
    "Генерируешь идеи постов для корпоративных соцсетей на русском языке."
)

_USER_TMPL = (
    "Источник контента: «{name}» ({url}).\n"
    "Придумай {n} идеи постов, вдохновлённых этим источником.\n"
    "Верни строго JSON-массив без markdown-обёртки:\n"
    '[{{"title": "...", "body_md": "..."}}, ...]\n'
    "title — заголовок до 80 символов. body_md — текст поста 80–200 слов."
)


class AISourcesService:
    def __init__(self, metadata: MetaData) -> None:
        self.posts = PostsRepo(metadata)
        self.sources = SourcesRepo(metadata)

    async def ideas_from_sources(
        self,
        db: AsyncSession,
        source_ids: List[int] | None,
        limit_per_source: int = 3,
    ) -> list[int]:
        """Генерирует черновики-идеи для каждого источника через OpenAI."""
        all_src = await self.sources.list(db)
        if source_ids:
            src_map = {s["source_id"]: s for s in all_src if s["source_id"] in source_ids}
        else:
            src_map = {s["source_id"]: s for s in all_src}

        created: list[int] = []
        for src in src_map.values():
            ideas = await self._call_llm(
                name=src.get("name", "источник"),
                url=src.get("url", ""),
                n=min(limit_per_source, 10),
            )
            for idea in ideas:
                data = {
                    "channel_id": 1,
                    "format_id": 1,
                    "topic_id": 1,
                    "direction_id": None,
                    "title": idea["title"],
                    "text": idea["body_md"],
                    "planned_for": None,
                    "source_code": "ai_generated",
                }
                pid = await self.posts.create_draft_post(db, data)
                created.append(pid)
        return created

    async def _call_llm(self, name: str, url: str, n: int) -> list[dict]:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY не задан — возвращаем заглушку")
            return [
                {"title": f"Идея из «{name}» #{i}", "body_md": f"Пост на основе источника {name}."}
                for i in range(1, n + 1)
            ]

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _USER_TMPL.format(name=name, url=url, n=n)},
                ],
                temperature=0.8,
                max_tokens=2048,
            )
            raw = resp.choices[0].message.content or "[]"
            return json.loads(raw)
        except Exception:
            logger.exception("OpenAI ошибка для источника %s, используем fallback", name)
            return [
                {"title": f"Идея из «{name}» #{i}", "body_md": f"Пост на основе источника {name}."}
                for i in range(1, n + 1)
            ]
