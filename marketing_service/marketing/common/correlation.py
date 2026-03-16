"""Корреляция запросов.

Что делает:
- Генерирует/прокидывает X-Correlation-Id для трассировки цепочки вызовов.
"""
from __future__ import annotations
import uuid
from fastapi import Header

async def correlation_id(x_correlation_id: str | None = Header(default=None)) -> str:
    return x_correlation_id or f"mk-{uuid.uuid4()}"
