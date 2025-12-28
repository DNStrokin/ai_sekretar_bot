"""
WebApp API Routes

API для Telegram WebApp (Mini App) — управление темами и настройками.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(tags=["webapp"])


# ============ Schemas ============

class TopicBase(BaseModel):
    title: str
    description: Optional[str] = None
    format_policy_text: Optional[str] = None


class TopicUpdate(BaseModel):
    description: Optional[str] = None
    format_policy_text: Optional[str] = None


class TopicResponse(TopicBase):
    id: int
    telegram_topic_id: int
    is_active: bool

    class Config:
        from_attributes = True


class AISettingsUpdate(BaseModel):
    provider: Optional[str] = None  # "openai" or "gemini"
    model: Optional[str] = None
    brevity_level: Optional[int] = None  # 1-5


class AISettingsResponse(BaseModel):
    provider: str
    model: str
    brevity_level: int


# ============ Topics ============

@router.get("/topics", response_model=list[TopicResponse])
async def list_topics():
    """Get all topics for the group."""
    # TODO: Implement database query
    return []


@router.get("/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: int):
    """Get a specific topic by ID."""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Topic not found")


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: int, topic: TopicUpdate):
    """Update topic description or format policy."""
    # TODO: Implement database update
    raise HTTPException(status_code=404, detail="Topic not found")


@router.post("/topics/sync")
async def sync_topics():
    """Sync topics from Telegram group."""
    # TODO: Implement Telegram API call to fetch topics
    return {"status": "ok", "synced_count": 0}


# ============ AI Settings ============

@router.get("/settings/ai", response_model=AISettingsResponse)
async def get_ai_settings():
    """Get current AI settings."""
    # TODO: Implement database query
    return AISettingsResponse(
        provider="gemini",
        model="gemini-pro",
        brevity_level=3
    )


@router.patch("/settings/ai", response_model=AISettingsResponse)
async def update_ai_settings(settings: AISettingsUpdate):
    """Update AI settings."""
    # TODO: Implement database update
    return AISettingsResponse(
        provider=settings.provider or "gemini",
        model=settings.model or "gemini-pro",
        brevity_level=settings.brevity_level or 3
    )
