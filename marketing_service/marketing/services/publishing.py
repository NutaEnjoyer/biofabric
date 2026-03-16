"""Публикация в Telegram/VK по кнопке «Опубликовать сейчас».

MVP: без расписаний, только немедленная публикация."""
from typing import Any, Optional
import httpx
from ..config import settings


class PublishingService:
    async def publish_now_tg(self, text: str) -> str:
        """Публикация в Telegram-канал через бота.

        Возвращает ссылку на опубликованное сообщение (если возможно её построить)."""
        if not (settings.TG_BOT_TOKEN and settings.TG_CHANNEL_ID):
            raise RuntimeError("TG is not configured")
        url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json={"chat_id": settings.TG_CHANNEL_ID, "text": text})
            r.raise_for_status()
            data = r.json()
            # формируем ссылку, если это публичный канал (упрощённо)
            message_id = data.get("result", {}).get("message_id")
            return f"https://t.me/c/{settings.TG_CHANNEL_ID}/{message_id}" if message_id else ""

    async def publish_now_vk(self, text: str) -> str:
        """Публикация в VK группу.

        Упрощённо: только текстовый пост для MVP."""
        if not (settings.VK_GROUP_TOKEN and settings.VK_GROUP_ID):
            raise RuntimeError("VK is not configured")
        url = "https://api.vk.com/method/wall.post"
        params = {
            "owner_id": f"-{settings.VK_GROUP_ID}",  # группы — отрицательный owner_id
            "from_group": 1,
            "message": text,
            "access_token": settings.VK_GROUP_TOKEN,
            "v": "5.199"
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, data=params)
            r.raise_for_status()
            data = r.json()
            post_id = data.get("response", {}).get("post_id")
            return f"https://vk.com/wall-{settings.VK_GROUP_ID}_{post_id}" if post_id else ""
