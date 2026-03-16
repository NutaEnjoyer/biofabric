"""Общие Depends для API.

- get_db(): выдаёт асинхронную сессию БД
- get_core(correlation): создаёт CoreClient
- get_user(): заглушка для текущего пользователя
- can(...): RBAC проверка действий
"""
from __future__ import annotations
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_session
from ..common.correlation import correlation_id
from ..core_client.client import CoreClient
from ..security.rbac import can
from ..config import settings


async def get_db() -> AsyncSession:
    async with get_session() as s:
        yield s


async def get_core(cid: str = Depends(correlation_id)) -> CoreClient:
    return CoreClient(correlation_id=cid)


# Заглушка пользователя; в реальном коде подтягиваем из авторизации
class User:
    def __init__(self, user_id: int = 1, roles: list[str] = ["admin"]) -> None:
        self.user_id = user_id
        self.roles = roles


async def get_user() -> User:
    return User()


__all__ = ["get_db", "get_core", "get_user", "can"]
