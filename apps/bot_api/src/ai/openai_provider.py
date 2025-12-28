"""
OpenAI Provider Implementation

Интеграция с OpenAI API (ChatGPT, Whisper).
"""

import json
from typing import Optional

from .base import AIProvider, ClassificationResult, RenderedNote, TopicContext
from settings.config import settings


class OpenAIProvider(AIProvider):
    """OpenAI API implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        # TODO: Initialize OpenAI client

    async def classify_note(
        self,
        note_text: str,
        topics: list[TopicContext]
    ) -> ClassificationResult:
        """Classify note using OpenAI."""
        # TODO: Implement OpenAI API call
        # For now, return placeholder
        return ClassificationResult(
            suggested_topic_id=topics[0].topic_id if topics else 0,
            top_topics=[],
            need_new_topic=len(topics) == 0
        )

    async def render_note(
        self,
        note_text: str,
        topic: TopicContext
    ) -> RenderedNote:
        """Format note using OpenAI."""
        # TODO: Implement OpenAI API call
        return RenderedNote(
            title="Заголовок заметки",
            content=note_text,
            tags=["#заметка"]
        )

    async def transcribe_voice(self, audio_data: bytes) -> str:
        """Transcribe using Whisper API."""
        # TODO: Implement Whisper API call
        return ""
