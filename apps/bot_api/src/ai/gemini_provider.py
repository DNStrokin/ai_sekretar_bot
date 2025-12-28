"""
Gemini Provider Implementation

Интеграция с Google Gemini via google-generativeai.
"""

import json
import logging
from typing import Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import AIProvider, ClassificationResult, RenderedNote, TopicContext
from src.settings.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini API implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY не задан. AI функции работать не будут.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            # Используем gemini-pro (или gemini-1.5-flash, если доступна, но начнем с pro)
            # Для структурированного вывода лучше использовать модель поновее, если есть
            self.model = genai.GenerativeModel('gemini-1.5-flash') 

    async def classify_note(
        self,
        note_text: str,
        topics: list[TopicContext]
    ) -> ClassificationResult:
        """Classify note using Gemini."""
        if not self.model or not topics:
            return ClassificationResult(suggested_topic_id=0, top_topics=[], need_new_topic=True)

        topics_str = json.dumps([
            {
                "id": t.topic_id, 
                "title": t.title, 
                "description": t.description
            } 
            for t in topics
        ], ensure_ascii=False)

        prompt = (
            "You are a smart assistant that sorts notes into topics.\n"
            f"Allowed topics: {topics_str}\n\n"
            "Task: Analyze the user's note and select the most appropriate topic ID.\n"
            "If none of the topics fit perfectly, but one is close, choose it.\n"
            "If the note is completely unrelated to any existing topic, set id=0 (new topic).\n\n"
            "Return JSON only: {\"id\": <topic_id>, \"confidence\": <0.0-1.0>}"
        )

        try:
            # Gemini требует явного указания MIME типа для JSON режима в некоторых версиях,
            # но простой промпт "Return JSON only" обычно работает.
            # Для надежности можно использовать generation_config={'response_mime_type': 'application/json'}
            # если модель поддерживает. gemini-1.5-flash поддерживает.
            
            response = await self.model.generate_content_async(
                [prompt, note_text],
                generation_config={"response_mime_type": "application/json"}
            )
            
            content = response.text
            data = json.loads(content)
            
            topic_id = data.get("id", 0)
            
            # Валидация
            if topic_id != 0 and not any(t.topic_id == topic_id for t in topics):
                topic_id = 0
            
            return ClassificationResult(
                suggested_topic_id=topic_id,
                top_topics=[{"topic_id": topic_id, "confidence": data.get("confidence", 0.0)}],
                need_new_topic=(topic_id == 0)
            )

        except Exception as e:
            logger.error(f"Error classifying note with Gemini: {e}")
            return ClassificationResult(suggested_topic_id=0, top_topics=[], need_new_topic=True)

    async def render_note(
        self,
        note_text: str,
        topic: TopicContext
    ) -> RenderedNote:
        """Format note using Gemini."""
        if not self.model:
             return RenderedNote(title="Заметка", content=note_text, tags=[])

        format_rules = topic.format_policy_text or "Create a concise title, summarize the content, and extract tags."
        
        prompt = (
            "You are a professional editor. Format the user's raw text into a clean note.\n"
            f"Context (Topic): {topic.title}\n"
            f"Formatting Rules: {format_rules}\n\n"
            "Task:\n"
            "1. Create a short, descriptive emoji title.\n"
            "2. Clean up and format the content (fix grammar, use lists if appropriate).\n"
            "3. Extract key tags (hashtags).\n\n"
            "Return JSON only: {\"title\": \"...\", \"content\": \"...\", \"tags\": [\"#tag1\", ...]}"
        )

        try:
            response = await self.model.generate_content_async(
                [prompt, note_text],
                generation_config={"response_mime_type": "application/json"}
            )
            
            content = response.text
            data = json.loads(content)
            
            title = data.get("title", "Заметка")
            formatted_content = data.get("content", note_text)
            tags = data.get("tags", [])
            
            # Ensure tags start with #
            formatted_tags = [t if t.startswith('#') else f"#{t}" for t in tags]
            
            return RenderedNote(
                title=title,
                content=formatted_content,
                tags=formatted_tags
            )

        except Exception as e:
            logger.error(f"Error rendering note with Gemini: {e}")
            return RenderedNote(title="Заметка", content=note_text, tags=[])

    async def transcribe_voice(self, audio_data: bytes) -> str:
        """Transcribe using Gemini (multimodal)."""
        # TODO: Implement Gemini audio transcription
        return ""
