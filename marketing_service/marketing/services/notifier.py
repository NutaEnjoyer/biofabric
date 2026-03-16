"""Сервис уведомлений модуля Маркетинг.

Реализует 4 события из ТЗ п.9:
  N1 — Не хватает контента на ближайшую неделю  (интерфейс, push)
  N2 — Пост сформирован ИИ                      (интерфейс, системное)
  N3 — Приближается дата публикации              (мессенджер, push)
  N4 — Пост утверждён                            (интерфейс, push)

Все уведомления делегируются в ядро через CoreClient.notify().
"""
from __future__ import annotations
from typing import Any
from ..core_client.client import CoreClient


class MarketingNotifier:
    def __init__(self, core: CoreClient) -> None:
        self.core = core

    # N1 — Не хватает контента на ближайшую неделю
    async def content_gap_warning(self, gaps: list[dict[str, Any]]) -> None:
        """Уведомляет, что на ближайшей неделе есть дни без контента.

        Вызывается из GET /analytics/gaps, если список не пуст.
        Канал: интерфейс (push).
        """
        days = ", ".join(str(g.get("day")) for g in gaps)
        await self.core.notify(
            user_id=None,  # широковещательное — всем маркетологам
            event_type="content_gap",
            message=f"Не хватает контента на ближайшую неделю. Дни без постов: {days}",
            meta={"gaps": gaps},
        )

    # N2 — Пост сформирован ИИ
    async def ai_post_created(self, post_ids: list[int], user_id: int | None = None) -> None:
        """Уведомляет редактора о том, что ИИ сгенерировал черновики.

        Вызывается после POST /ai/plan и POST /ai/ideas.
        Канал: интерфейс (системное).
        """
        await self.core.notify(
            user_id=user_id,
            event_type="ai_post_created",
            message=f"ИИ сформировал {len(post_ids)} черновик(а/ов). Проверьте и утвердите.",
            meta={"post_ids": post_ids},
        )

    # N3 — Приближается дата публикации
    async def post_due_soon(self, post_id: int, planned_for: str, user_id: int | None = None) -> None:
        """Уведомляет ответственного о том, что дата публикации поста приближается (≤ 3 дня).

        Вызывается из deadline_checker.notify_upcoming_posts().
        Канал: мессенджер (push).
        """
        await self.core.notify(
            user_id=user_id,
            event_type="post_due",
            message=f"Пост #{post_id} запланирован на {planned_for} — осталось менее 3 дней.",
            meta={"post_id": post_id, "planned_for": planned_for},
        )

    # N4 — Пост утверждён
    async def post_approved(self, post_id: int, author_user_id: int | None = None) -> None:
        """Уведомляет автора об утверждении поста.

        Вызывается при переводе поста в статус 'approved'.
        Канал: интерфейс (push).
        """
        await self.core.notify(
            user_id=author_user_id,
            event_type="post_approved",
            message=f"Пост #{post_id} утверждён и готов к публикации.",
            meta={"post_id": post_id},
        )
