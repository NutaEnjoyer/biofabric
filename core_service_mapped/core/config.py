from pydantic_settings import BaseSettings
from pydantic import Field
class Settings(BaseSettings):
    DATABASE_URL: str = Field(...)
    JWT_ACCESS_SECRET: str = Field(...)
    JWT_REFRESH_SECRET: str = Field(...)
    ONLYOFFICE_BASE_URL: str = Field(...)
    ONLYOFFICE_JWT_SECRET: str = Field(...)
    ONLYOFFICE_WEBHOOK_SECRET: str = Field(...)
    OO_CALLBACK_URL: str = Field(...)
    SMTP_HOST: str = Field(...)
    SMTP_PORT: int = Field(...)
    SMTP_USER: str = Field(...)
    SMTP_PASSWORD: str = Field(...)
    SMTP_FROM: str = Field(...)
    TELEGRAM_BOT_TOKEN: str = Field(...)
    OPENAI_API_KEY: str = Field(...)
    AI_PROXY_URL: str = Field(...)
    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
settings = Settings()
