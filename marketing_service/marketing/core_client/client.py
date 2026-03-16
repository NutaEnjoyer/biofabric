"""Клиент к ядру (Core API): workflow, docs, audit.

Что делает:
- Оборачивает вызовы к /v1/core/*, чтобы модуль не зависел от деталей протокола.
- В нашем MVP часть методов может быть no-op, если ядро ещё не подключено.
"""
from __future__ import annotations
import httpx
from typing import Any
from ..config import settings

class CoreClient:
    """Лёгкий HTTP-клиент к ядру.

    Использование:
    - Создаётся на каждый запрос с корреляционным id.
    - Методы возвращают dict-ответы или поднимают исключения по 4xx/5xx.
    """
    def __init__(self, correlation_id: str):
        self.base_url = settings.CORE_BASE_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {settings.CORE_BEARER}",
            "X-Correlation-Id": correlation_id
        }

    async def _post(self, path: str, payload: dict[str, Any], critical: bool = False) -> dict[str, Any]:
        """Внутренний метод: POST к ядру с обработкой ошибок.

        critical=False — при недоступности ядра логируем и продолжаем работу.
        """
        import logging
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(url, headers=self.headers, json=payload)
                r.raise_for_status()
                return r.json()
        except Exception as exc:
            if critical:
                raise
            logging.getLogger("core_client").warning("Core call %s failed (non-critical): %s", url, exc)
            return {}

    async def advance_workflow(self, entity_type: str, entity_id: str, transition: str) -> dict[str, Any]:
        """Переводит сущность в новое состояние workflow в ядре (non-critical)."""
        return await self._post(
            "/workflow/advance",
            {"entity_type": entity_type, "entity_id": entity_id, "transition": transition},
        )

    async def bind_document(self, entity_type: str, entity_id: str, document_id: int) -> dict[str, Any]:
        """Привязывает документ к сущности в ядре (non-critical)."""
        return await self._post(
            "/docs/bind",
            {"entity_type": entity_type, "entity_id": entity_id, "document_id": document_id},
        )

    async def audit(self, action: str, entity_type: str, entity_id: str, meta: dict[str, Any] | None = None) -> None:
        """Пишет аудит-событие в ядро (non-critical)."""
        await self._post(
            "/audit/log",
            {"action": action, "entity_type": entity_type, "entity_id": entity_id, "meta": meta or {}},
        )

    async def notify(
        self,
        user_id: int | None,
        event_type: str,
        message: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Отправляет уведомление через ядро (non-critical).

        Параметры:
        - user_id: кому (None — широковещательное)
        - event_type: тип события ('content_gap', 'ai_post_created', 'post_approved', 'post_due')
        - message: текст уведомления
        - meta: доп. данные (post_id, date и пр.)
        """
        await self._post(
            "/notifications/send",
            {"user_id": user_id, "event_type": event_type, "message": message, "meta": meta or {}},
        )
