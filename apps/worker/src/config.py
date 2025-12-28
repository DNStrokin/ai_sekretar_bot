"""
Worker Configuration

Настройки воркера через pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Worker settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sekretar"

    # Telegram (for downloading files)
    TELEGRAM_BOT_TOKEN: str

    # AI Keys (for STT)
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # Worker settings
    WORKER_CONCURRENCY: int = 2
    LOG_LEVEL: str = "INFO"


settings = WorkerSettings()
