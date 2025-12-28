"""
AI Provider Base Interface

Единый интерфейс для работы с LLM провайдерами.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    """Result of note classification."""
    suggested_topic_id: int
    top_topics: list[dict]  # [{"topic_id": int, "confidence": float}]
    need_new_topic: bool


@dataclass
class RenderedNote:
    """Formatted note ready for publishing."""
    title: str
    content: str
    tags: list[str]


@dataclass
class TopicContext:
    """Topic information for classification/rendering."""
    topic_id: int
    title: str
    description: Optional[str] = None
    format_policy_text: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def classify_note(
        self,
        note_text: str,
        topics: list[TopicContext]
    ) -> ClassificationResult:
        """
        Classify a note into one of the available topics.
        
        Args:
            note_text: The text of the note to classify
            topics: List of available topics
            
        Returns:
            ClassificationResult with suggested topic and confidence scores
        """
        pass

    @abstractmethod
    async def render_note(
        self,
        note_text: str,
        topic: TopicContext
    ) -> RenderedNote:
        """
        Format a note according to topic's format policy.
        
        Args:
            note_text: Original note text
            topic: Target topic with formatting rules
            
        Returns:
            Formatted note ready for publishing
        """
        pass

    @abstractmethod
    async def transcribe_voice(self, audio_data: bytes) -> str:
        """
        Transcribe voice message to text.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Transcribed text
        """
        pass
