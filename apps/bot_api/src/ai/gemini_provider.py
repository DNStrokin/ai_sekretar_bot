"""
Google Gemini Provider Implementation

Интеграция с Google Gemini API.
"""

import json
from typing import Optional

from .base import AIProvider, ClassificationResult, RenderedNote, TopicContext
from src.settings.config import settings


class GeminiProvider(AIProvider):
    """Google Gemini API implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        # TODO: Initialize Gemini client

    async def classify_note(
        self,
        note_text: str,
        topics: list[TopicContext]
    ) -> ClassificationResult:
        """Classify note using Gemini."""
        # TODO: Implement Gemini API call
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
        """Format note using Gemini."""
        # TODO: Implement Gemini API call
        return RenderedNote(
            title="Заголовок заметки",
            content=note_text,
            tags=["#заметка"]
        )

    async def transcribe_voice(self, audio_data: bytes) -> str:
        """Transcribe using Google Speech API."""
        # TODO: Implement Google Speech API call
        return ""
