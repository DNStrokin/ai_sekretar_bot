"""
Database Models

SQLAlchemy модели для хранения метаданных.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """Telegram user."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    groups: Mapped[list["Group"]] = relationship(back_populates="user")
    ai_settings: Mapped["AISettings"] = relationship(back_populates="user", uselist=False)


class Group(Base):
    """Telegram group with topics enabled."""
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_group_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    topics_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="groups")
    topics: Mapped[list["Topic"]] = relationship(back_populates="group")


class Topic(Base):
    """Telegram forum topic within a group."""
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_topic_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    format_policy_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    group: Mapped["Group"] = relationship(back_populates="topics")


class AISettings(Base):
    """User's AI provider settings."""
    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(50), default="gemini")  # "openai" or "gemini"
    model: Mapped[str] = mapped_column(String(100), default="gemini-pro")
    brevity_level: Mapped[int] = mapped_column(Integer, default=3)  # 1-5
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="ai_settings")


class PendingConfirmation(Base):
    """Temporary storage for pending note confirmations."""
    __tablename__ = "pending_confirmations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    source_message_id: Mapped[int] = mapped_column(BigInteger)
    prepared_content: Mapped[str] = mapped_column(Text)  # JSON with prepared note
    suggested_topics: Mapped[str] = mapped_column(Text)  # JSON with topic IDs and scores
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)  # TTL

    # Relationships
    user: Mapped["User"] = relationship()
