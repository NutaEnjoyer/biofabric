"""Проверка приближающихся дат публикации (ТЗ п.9 N3).

Логика:
- Выбирает посты в статусе approved/scheduled с planned_for <= now + 3 дня.
- Для каждого такого поста отправляет push-уведомление через MarketingNotifier.

Использование:
    Вызывать вручную из эндпоинта или периодически (cron/celery — вне MVP).
    Пример: GET /v1/marketing/admin/notify-upcoming
"""
from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ..core_client.client import CoreClient
from .notifier import MarketingNotifier


async def notify_upcoming_posts(db: AsyncSession, core: CoreClient) -> list[int]:
    """Рассылает уведомления о постах, до публикации которых осталось ≤ 3 дня.

    Возвращает список post_id, для которых было отправлено уведомление.
    """
    # VIEW v_mk_posts_due_3d уже содержит нужный фильтр (статус + дата)
    res = await db.execute(text("SELECT post_id, planned_for, created_by FROM v_mk_posts_due_3d"))
    rows = res.mappings().all()
    notifier = MarketingNotifier(core)
    notified: list[int] = []
    for row in rows:
        await notifier.post_due_soon(
            post_id=row["post_id"],
            planned_for=str(row["planned_for"]),
            user_id=row.get("created_by"),
        )
        notified.append(row["post_id"])
    return notified
