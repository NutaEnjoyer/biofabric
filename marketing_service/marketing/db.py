"""Доступ к Postgres (асинхронный SQLAlchemy).

Что делает:
- Создаёт движок и фабрику сессий.
- Предоставляет вспомогательную функцию для dependency.
- Отражает таблицы по месту (reflection), чтобы не ломаться при дельтах.
  Это гарантирует «точный маппинг» без дублирования DDL в коде.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

metadata = MetaData()


async def init_db() -> None:
    """Отражает все таблицы БД один раз при старте приложения.

    Используется в lifespan FastAPI. После вызова metadata.tables
    будет содержать все нужные таблицы, и репозитории могут работать
    без повторного reflection.
    """
    async with engine.connect() as conn:
        await conn.run_sync(metadata.reflect)

@asynccontextmanager
async def get_session():
    """Dependency для FastAPI: даёт асинхронную сессию транзакции.

    Как работает:
    - Открывает сессию к БД.
    - Передаёт её в обработчик запроса.
    - Закрывает по завершении, делая commit/rollback на уровне вызвавшего кода.
    """
    async with SessionLocal() as session:
        yield session
