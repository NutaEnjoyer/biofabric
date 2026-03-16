"""Аналитические эндпоинты модуля Маркетинг.

Все данные берутся из VIEW, созданных в v8_marketing.sql.
Эндпоинты соответствуют ТЗ п.7–8 (анализ, агрегация).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..api.deps import get_db, get_core
from ..schemas.dto_common import ResponseOk
from ..repositories.analytics_repo import AnalyticsRepo
from ..services.notifier import MarketingNotifier
from ..services.deadline_checker import notify_upcoming_posts

router = APIRouter()


def _repo(db: AsyncSession) -> AnalyticsRepo:
    return AnalyticsRepo()


@router.get("/analytics/summary", response_model=ResponseOk)
async def plan_summary(db: AsyncSession = Depends(get_db)):
    """Сводка: число постов по дням, каналам и статусам.

    ТЗ п.7: «Число публикаций в периоде» + «Статусы подготовки»."""
    rows = await _repo(db).plan_summary(db)
    return ResponseOk(data=rows)


@router.get("/analytics/by-topic", response_model=ResponseOk)
async def by_topic(db: AsyncSession = Depends(get_db)):
    """Распределение контента по рубрикам.

    ТЗ п.7: «Распределение контента по рубрикам, типам и каналам»."""
    rows = await _repo(db).by_topic(db)
    return ResponseOk(data=rows)


@router.get("/analytics/by-format", response_model=ResponseOk)
async def by_format(db: AsyncSession = Depends(get_db)):
    """Распределение по форматам контента (текст, инфографика, новость и пр.).

    ТЗ п.8: «Объёмы по типам контента»."""
    rows = await _repo(db).by_format(db)
    return ResponseOk(data=rows)


@router.get("/analytics/by-channel", response_model=ResponseOk)
async def by_channel(db: AsyncSession = Depends(get_db)):
    """Распределение по каналам публикации.

    ТЗ п.8: «Частота публикаций в соцсетях по дням и неделям»."""
    rows = await _repo(db).by_channel(db)
    return ResponseOk(data=rows)


@router.get("/analytics/density", response_model=ResponseOk)
async def calendar_density(db: AsyncSession = Depends(get_db)):
    """Насыщенность сетки: сколько постов запланировано на каждый день.

    ТЗ п.7: «Загрузка по датам (насыщенность сетки)»."""
    rows = await _repo(db).density(db)
    return ResponseOk(data=rows)


@router.post("/analytics/notify-upcoming", response_model=ResponseOk)
async def notify_upcoming(db: AsyncSession = Depends(get_db), core=Depends(get_core)):
    """Разослать N3-уведомления о постах, до публикации которых ≤ 3 дня.

    ТЗ п.9 N3: «Приближается дата публикации» → push в мессенджер.
    Вызывать вручную или из планировщика задач."""
    notified = await notify_upcoming_posts(db, core)
    return ResponseOk(data={"notified_post_ids": notified})


@router.get("/analytics/gaps", response_model=ResponseOk)
async def upcoming_gaps(db: AsyncSession = Depends(get_db), core=Depends(get_core)):
    """Дни ближайшей недели без контента по каналам.

    ТЗ п.9 N1: если список не пуст — автоматически отправляет push-уведомление
    «Не хватает контента на ближайшую неделю»."""
    rows = await _repo(db).gaps(db)
    # N1 — уведомление: нет контента на неделю
    if rows:
        await MarketingNotifier(core).content_gap_warning(rows)
    return ResponseOk(data=rows)


@router.get("/analytics/warnings", response_model=ResponseOk)
async def content_warnings(db: AsyncSession = Depends(get_db)):
    """Визуальные индикаторы «провалов» в контент-сетке (ТЗ п.4.3).

    Возвращает список предупреждений трёх типов:
    - content_gap: недостаточно контента на неделю
    - topic_skew: перекос по рубрике (>60% постов одной рубрики)
    - no_approved: нет утверждённых постов
    """
    rows = await _repo(db).warnings(db)
    return ResponseOk(data=rows)
