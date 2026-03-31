"""ИИ-генерация плана от промта (без дат)."""
from __future__ import annotations
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import MetaData
from typing import List
from openai import AsyncOpenAI
from ..repositories.posts_repo import PostsRepo
from ..config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Ты — контент-менеджер биофабрики. "
    "Пишешь тексты для корпоративных соцсетей на русском языке. "
    "Стиль: профессиональный, но понятный. Без воды."
)

_USER_TMPL = (
    "Создай {n} варианта поста для соцсетей по теме: «{prompt}».\n"
    "Верни строго JSON-массив объектов без markdown-обёртки:\n"
    '[{{"title": "...", "body_md": "..."}}, ...]\n'
    "title — короткий заголовок (до 80 символов).\n"
    "body_md — текст поста (100–300 слов, можно использовать эмодзи и абзацы)."
)


class AIPlanService:
    def __init__(self, metadata: MetaData) -> None:
        self.repo = PostsRepo(metadata)

    async def generate_from_prompt(
        self,
        db: AsyncSession,
        prompt: str,
        channels: List[int] | None,
        formats: List[int] | None,
        n: int = 3,
    ) -> list[int]:
        """Создаёт n черновиков на основе текстового промта через OpenAI."""
        posts = await self._call_llm(prompt, n)
        channel_id = (channels or [1])[0]
        format_id = (formats or [1])[0]

        post_ids: list[int] = []
        for p in posts:
            data = {
                "channel_id": channel_id,
                "format_id": format_id,
                "topic_id": 1,
                "direction_id": None,
                "title": p["title"],
                "text": p["body_md"],
                "planned_for": None,
                "source_code": "ai_generated",
            }
            pid = await self.repo.create_draft_post(db, data)
            post_ids.append(pid)
        return post_ids

    async def _call_llm(self, prompt: str, n: int) -> list[dict]:
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY не задан — возвращаем заглушку")
            return [
                {"title": f"Идея #{i}: {prompt[:40]}", "body_md": f"Черновик {i}: {prompt}"}
                for i in range(1, n + 1)
            ]

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _USER_TMPL.format(n=n, prompt=prompt)},
                ],
                temperature=0.8,
                max_tokens=2048,
            )
            raw = resp.choices[0].message.content or "[]"
            return json.loads(raw)
        except Exception:
            logger.exception("OpenAI вернул ошибку, используем fallback")
            return [
                {"title": f"Идея #{i}: {prompt[:40]}", "body_md": f"Черновик {i}: {prompt}"}
                for i in range(1, n + 1)
            ]
