"""
Application Configuration

Настройки приложения через pydantic-settings.
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Определяем путь к .env файлу (в корне проекта)
def _find_env_file() -> str:
    """Найти .env файл в корне проекта."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # Максимум 5 уровней вверх
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            return env_path
        current = os.path.dirname(current)
    return ".env"


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_GROUP_ID: Optional[int] = None  # Опционально — определяется автоматически
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    USE_POLLING: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/sekretar"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security
    SECRET_KEY: str = "change-me-in-production"

    @field_validator("TELEGRAM_GROUP_ID", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Конвертирует пустую строку в None."""
        if v == "" or v is None:
            return None
        return int(v)
    
    @field_validator("OPENAI_API_KEY", "GEMINI_API_KEY", "TELEGRAM_WEBHOOK_URL", mode="before")
    @classmethod
    def empty_str_to_none_str(cls, v):
        """Конвертирует пустую строку в None для строковых полей."""
        if v == "":
            return None
        return v


# Глобальный экземпляр настроек
settings = Settings()
