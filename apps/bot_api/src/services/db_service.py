import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User, Group, Topic

logger = logging.getLogger(__name__)

async def get_or_create_user(session: AsyncSession, telegram_user_id: int) -> User:
    """Получить или создать пользователя."""
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(telegram_user_id=telegram_user_id)
        session.add(user)
        # Commit обычно делается на уровне выше, но тут для гарантии ID можно сделать flush
        # Однако, в оригинальном коде был commit. 
        # Оставим flush для получения ID, коммит будет снаружи или здесь если это атомарная операция
        await session.commit() 
        await session.refresh(user)
        logger.info(f"Создан новый пользователь: {telegram_user_id}")
    
    return user


async def get_or_create_group(
    session: AsyncSession, 
    user_id: int, 
    chat_id: int, 
    title: str = "Без названия", 
    is_forum: bool = False
) -> Group:
    """Получить или создать группу."""
    result = await session.execute(
        select(Group).where(Group.telegram_group_id == chat_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        group = Group(
            telegram_group_id=chat_id,
            title=title,
            topics_enabled=is_forum,
            user_id=user_id
        )
        session.add(group)
        await session.commit()
        await session.refresh(group)
        logger.info(f"Создана новая группа: {title} ({chat_id})")
    else:
        # Обновляем инфо если нужно
        if group.title != title or group.topics_enabled != is_forum:
            group.title = title
            group.topics_enabled = is_forum
            await session.commit()
    
    return group


async def get_user_group(session: AsyncSession, telegram_user_id: int) -> Optional[Group]:
    """Получить группу пользователя."""
    result = await session.execute(
        select(Group)
        .join(User)
        .where(User.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def get_topic(session: AsyncSession, group_id: int, telegram_topic_id: int) -> Optional[Topic]:
    """Получить тему по ID."""
    result = await session.execute(
        select(Topic).where(
            Topic.group_id == group_id,
            Topic.telegram_topic_id == telegram_topic_id
        )
    )
    return result.scalar_one_or_none()


async def create_topic(
    session: AsyncSession, 
    group_id: int, 
    telegram_topic_id: int, 
    title: str = "Тема"
) -> Topic:
    """Создать новую тему."""
    topic = Topic(
        telegram_topic_id=telegram_topic_id,
        title=title,
        group_id=group_id,
        is_active=True
    )
    session.add(topic)
    await session.commit()
    return topic
