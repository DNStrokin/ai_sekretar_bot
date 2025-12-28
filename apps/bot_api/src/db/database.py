"""
Database Connection and Session Management

Настройка SQLAlchemy async engine и сессий.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


def get_database_url() -> str:
    """Получить URL базы данных из переменных окружения."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/sekretar"
    )


def get_engine():
    """Создать async engine."""
    from src.settings.config import settings
    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True
    )


# Lazy initialization
_engine = None
_async_session_maker = None


def get_async_session_maker():
    """Получить фабрику сессий (lazy init)."""
    global _engine, _async_session_maker
    if _async_session_maker is None:
        _engine = get_engine()
        _async_session_maker = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_maker


async def init_db():
    """Инициализация базы данных (создание таблиц если нужно)."""
    engine = get_engine()
    async with engine.begin() as conn:
        # В production используйте Alembic миграции
        # Это только для разработки
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для получения сессии базы данных."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        yield session
