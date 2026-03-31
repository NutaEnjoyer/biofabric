"""Конфигурация модуля.

Что делает:
- Читает переменные окружения для подключения к БД и Core.
- Хранит константы (например, допустимые форматы).
- Используется всеми слоями сервиса.
"""
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/biolab"
    CORE_BASE_URL: str = "http://core:8080/v1/core"
    CORE_BEARER: str = "token"
    SERVICE_NAME: str = "marketing"

    TG_BOT_TOKEN: str | None = None
    TG_CHANNEL_ID: str | None = None

    VK_GROUP_TOKEN: str | None = None
    VK_GROUP_ID: str | None = None

    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()

# Базовый список форматов. Справочник лежит в БД; здесь — дефолт для валидации/подсказок.
DEFAULT_FORMATS = ["post", "story", "reel", "article", "рассылка"]
