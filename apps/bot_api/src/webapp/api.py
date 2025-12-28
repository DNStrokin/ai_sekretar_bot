"""
WebApp API Routes

API для Telegram WebApp (Mini App) — управление темами и настройками.
"""

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_async_session_maker
from src.db.models import User, Group, Topic, AISettings
from src.settings.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webapp"])


# ============ Schemas ============

class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    format_policy_text: Optional[str] = None


class TopicUpdate(BaseModel):
    description: Optional[str] = None
    format_policy_text: Optional[str] = None


class TopicResponse(BaseModel):
    id: int
    telegram_topic_id: int
    title: str
    description: Optional[str] = None
    format_policy_text: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class AISettingsUpdate(BaseModel):
    provider: Optional[str] = None  # "openai" или "gemini"
    model: Optional[str] = None
    brevity_level: Optional[int] = None  # 1-5


class AISettingsResponse(BaseModel):
    provider: str
    model: str
    brevity_level: int

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: int
    title: str
    telegram_group_id: int
    topics_enabled: bool

    class Config:
        from_attributes = True


# ============ Auth Helpers ============

def validate_telegram_init_data(init_data: str) -> dict | None:
    """
    Валидация Telegram WebApp initData.
    Возвращает распарсенные данные или None если невалидны.
    """
    if not init_data:
        return None
    
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        
        # Получаем hash из данных
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        
        # Сортируем оставшиеся параметры
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        
        # Вычисляем secret_key
        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if computed_hash == received_hash:
            # Парсим user
            if "user" in parsed:
                parsed["user"] = json.loads(parsed["user"])
            return parsed
        
        return None
    except Exception as e:
        logger.error(f"Ошибка валидации initData: {e}")
        return None


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data")
) -> User:
    """
    Получить текущего пользователя из Telegram initData.
    """
    # Для разработки: если нет initData, используем первого пользователя
    if not x_telegram_init_data or settings.DEBUG:
        session_maker = get_async_session_maker()
        async with session_maker() as session:
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            if user:
                return user
    
    # Валидация initData
    data = validate_telegram_init_data(x_telegram_init_data)
    if not data or "user" not in data:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    
    telegram_user_id = data["user"]["id"]
    
    # Получаем пользователя из БД
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user


# ============ Group ============

@router.get("/group", response_model=Optional[GroupResponse])
async def get_group(user: User = Depends(get_current_user)):
    """Получить группу пользователя."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(Group).where(Group.user_id == user.id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return None
        
        return GroupResponse(
            id=group.id,
            title=group.title,
            telegram_group_id=group.telegram_group_id,
            topics_enabled=group.topics_enabled
        )


# ============ Topics ============

@router.get("/topics", response_model=list[TopicResponse])
async def list_topics(user: User = Depends(get_current_user)):
    """Получить все темы группы пользователя."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Получаем группу пользователя
        group_result = await session.execute(
            select(Group).where(Group.user_id == user.id)
        )
        group = group_result.scalar_one_or_none()
        
        if not group:
            return []
        
        # Получаем темы
        topics_result = await session.execute(
            select(Topic).where(Topic.group_id == group.id)
        )
        topics = topics_result.scalars().all()
        
        return [
            TopicResponse(
                id=t.id,
                telegram_topic_id=t.telegram_topic_id,
                title=t.title,
                description=t.description,
                format_policy_text=t.format_policy_text,
                is_active=t.is_active
            )
            for t in topics
        ]


@router.get("/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: int, user: User = Depends(get_current_user)):
    """Получить конкретную тему по ID."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Проверяем, что тема принадлежит пользователю
        result = await session.execute(
            select(Topic)
            .join(Group)
            .where(Topic.id == topic_id, Group.user_id == user.id)
        )
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        return TopicResponse(
            id=topic.id,
            telegram_topic_id=topic.telegram_topic_id,
            title=topic.title,
            description=topic.description,
            format_policy_text=topic.format_policy_text,
            is_active=topic.is_active
        )


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: int, 
    topic_update: TopicUpdate,
    user: User = Depends(get_current_user)
):
    """Обновить описание или правила форматирования темы."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Проверяем, что тема принадлежит пользователю
        result = await session.execute(
            select(Topic)
            .join(Group)
            .where(Topic.id == topic_id, Group.user_id == user.id)
        )
        topic = result.scalar_one_or_none()
        
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Обновляем поля
        if topic_update.description is not None:
            topic.description = topic_update.description
        if topic_update.format_policy_text is not None:
            topic.format_policy_text = topic_update.format_policy_text
        
        await session.commit()
        await session.refresh(topic)
        
        return TopicResponse(
            id=topic.id,
            telegram_topic_id=topic.telegram_topic_id,
            title=topic.title,
            description=topic.description,
            format_policy_text=topic.format_policy_text,
            is_active=topic.is_active
        )


@router.post("/topics/sync")
async def sync_topics(user: User = Depends(get_current_user)):
    """
    Синхронизировать темы из Telegram группы.
    
    Темы добавляются автоматически когда бот видит сообщения в группе.
    Эта функция создаёт демо-темы только если у пользователя ещё нет тем.
    """
    from src.services.topic_sync import create_default_topics
    
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        # Получаем группу пользователя
        result = await session.execute(
            select(Group).where(Group.user_id == user.id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(status_code=404, detail="Группа не найдена. Добавьте бота в группу.")
        
        # Проверяем есть ли уже темы
        topics_result = await session.execute(
            select(Topic).where(Topic.group_id == group.id)
        )
        existing_topics = topics_result.scalars().all()
        
        if existing_topics:
            return {
                "status": "ok",
                "message": f"Найдено {len(existing_topics)} тем",
                "synced_count": len(existing_topics)
            }
        
        # Создаём демо-темы только если тем нет
        topics = await create_default_topics(session, group.id)
        
        return {
            "status": "ok",
            "message": f"Создано {len(topics)} демо-тем (отправьте сообщения в темы группы для реальной синхронизации)",
            "synced_count": len(topics)
        }


# ============ AI Settings ============

@router.get("/settings/ai", response_model=AISettingsResponse)
async def get_ai_settings(user: User = Depends(get_current_user)):
    """Получить настройки AI пользователя."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(AISettings).where(AISettings.user_id == user.id)
        )
        ai_settings = result.scalar_one_or_none()
        
        if not ai_settings:
            # Возвращаем дефолтные настройки
            return AISettingsResponse(
                provider="gemini",
                model="gemini-pro",
                brevity_level=3
            )
        
        return AISettingsResponse(
            provider=ai_settings.provider,
            model=ai_settings.model,
            brevity_level=ai_settings.brevity_level
        )


@router.patch("/settings/ai", response_model=AISettingsResponse)
async def update_ai_settings(
    settings_update: AISettingsUpdate,
    user: User = Depends(get_current_user)
):
    """Обновить настройки AI."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(AISettings).where(AISettings.user_id == user.id)
        )
        ai_settings = result.scalar_one_or_none()
        
        if not ai_settings:
            # Создаём новые настройки
            ai_settings = AISettings(
                user_id=user.id,
                provider=settings_update.provider or "gemini",
                model=settings_update.model or "gemini-pro",
                brevity_level=settings_update.brevity_level or 3
            )
            session.add(ai_settings)
        else:
            # Обновляем существующие
            if settings_update.provider is not None:
                ai_settings.provider = settings_update.provider
            if settings_update.model is not None:
                ai_settings.model = settings_update.model
            if settings_update.brevity_level is not None:
                ai_settings.brevity_level = settings_update.brevity_level
        
        await session.commit()
        await session.refresh(ai_settings)
        
        return AISettingsResponse(
            provider=ai_settings.provider,
            model=ai_settings.model,
            brevity_level=ai_settings.brevity_level
        )
