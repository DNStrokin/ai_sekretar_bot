"""
Topic Sync Service

Синхронизация тем из Telegram группы.
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import ForumTopic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_async_session_maker
from src.db.models import User, Group, Topic

logger = logging.getLogger(__name__)


async def get_forum_topics(bot: Bot, chat_id: int) -> list[dict]:
    """
    Получить список тем форума из группы через Telegram Bot API.
    
    К сожалению, Telegram Bot API не предоставляет метод для получения
    всех тем форума. Есть только getForumTopicIconStickers.
    
    Альтернативный подход: бот отслеживает сообщения в темах и 
    автоматически добавляет их в БД при первом взаимодействии.
    """
    # Telegram Bot API пока не поддерживает получение списка тем
    # Используем альтернативный метод
    return []


async def sync_topics_from_messages(
    bot: Bot,
    user: User,
    session: AsyncSession
) -> dict:
    """
    Синхронизировать темы из группы пользователя.
    
    Так как Telegram API не даёт получить все темы напрямую,
    мы можем только добавлять темы при взаимодействии.
    """
    # Получаем группу пользователя
    result = await session.execute(
        select(Group).where(Group.user_id == user.id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        return {"status": "error", "message": "Группа не найдена"}
    
    if not group.topics_enabled:
        return {"status": "error", "message": "В группе не включены темы (форум)"}
    
    # Получаем информацию о группе
    try:
        chat = await bot.get_chat(group.telegram_group_id)
        
        # Проверяем что это форум
        if not getattr(chat, 'is_forum', False):
            group.topics_enabled = False
            await session.commit()
            return {"status": "error", "message": "Группа не является форумом"}
        
        # Обновляем название группы если изменилось
        if chat.title != group.title:
            group.title = chat.title
            await session.commit()
        
        return {
            "status": "ok",
            "message": "Информация о группе обновлена. Темы добавляются автоматически при взаимодействии.",
            "group_title": chat.title,
            "is_forum": True
        }
        
    except Exception as e:
        logger.error(f"Ошибка при синхронизации: {e}")
        return {"status": "error", "message": str(e)}


async def add_topic_if_not_exists(
    session: AsyncSession,
    group_id: int,
    telegram_topic_id: int,
    title: str = "Без названия"
) -> Topic:
    """
    Добавить тему в БД если её ещё нет.
    Вызывается когда бот видит сообщение в теме.
    """
    # Проверяем существует ли тема
    result = await session.execute(
        select(Topic).where(
            Topic.group_id == group_id,
            Topic.telegram_topic_id == telegram_topic_id
        )
    )
    topic = result.scalar_one_or_none()
    
    if topic:
        # Обновляем название если изменилось
        if topic.title != title:
            topic.title = title
            await session.commit()
        return topic
    
    # Создаём новую тему
    topic = Topic(
        telegram_topic_id=telegram_topic_id,
        title=title,
        group_id=group_id,
        is_active=True
    )
    session.add(topic)
    await session.commit()
    await session.refresh(topic)
    
    logger.info(f"Добавлена тема: {title} (id={telegram_topic_id})")
    return topic


async def create_default_topics(
    session: AsyncSession,
    group_id: int
) -> list[Topic]:
    """
    Создать стандартные темы для новой группы.
    Используется для демонстрации.
    """
    default_topics = [
        {"title": "💡 Идеи", "description": "Мысли, идеи, гипотезы для проектов"},
        {"title": "🛒 Покупки", "description": "Товары и услуги для покупки"},
        {"title": "📚 Книги", "description": "Книги для чтения и заметки"},
        {"title": "🎯 Цели", "description": "Цели и планы на будущее"},
    ]
    
    created_topics = []
    for i, t in enumerate(default_topics):
        topic = await add_topic_if_not_exists(
            session, 
            group_id, 
            telegram_topic_id=i + 1,  # Фиктивные ID для демо
            title=t["title"]
        )
        if topic.description != t["description"]:
            topic.description = t["description"]
        created_topics.append(topic)
    
    await session.commit()
    return created_topics
