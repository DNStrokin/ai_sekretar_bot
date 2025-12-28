"""
OpenAI Provider Implementation

Интеграция с OpenAI API (ChatGPT, Whisper).
"""

import json
import logging
from typing import Optional
from openai import AsyncOpenAI

from .base import AIProvider, ClassificationResult, RenderedNote, TopicContext
from src.settings.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI API implementation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("OPENAI_API_KEY не задан. AI функции работать не будут.")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=self.api_key)

    async def classify_note(
        self,
        note_text: str,
        topics: list[TopicContext]
    ) -> ClassificationResult:
        """Classify note using OpenAI."""
        if not self.client or not topics:
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
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # or gpt-3.5-turbo
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": note_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            topic_id = data.get("id", 0)
            
            # Валидация: проверяем что такой ID реально есть
            if topic_id != 0 and not any(t.topic_id == topic_id for t in topics):
                topic_id = 0
            
            return ClassificationResult(
                suggested_topic_id=topic_id,
                top_topics=[{"topic_id": topic_id, "confidence": data.get("confidence", 0.0)}],
                need_new_topic=(topic_id == 0)
            )

        except Exception as e:
            logger.error(f"Error classifying note: {e}")
            return ClassificationResult(suggested_topic_id=0, top_topics=[], need_new_topic=True)

    async def render_note(
        self,
        note_text: str,
        topic: TopicContext
    ) -> RenderedNote:
        """Format note using OpenAI."""
        if not self.client:
             return RenderedNote(title="Заметка", content=note_text, tags=[])

        # Для работы с системой шаблонов нам нужны чистые данные
        # format_rules мы больше не передаем в промпт для стиля.
        
        prompt = (
            "You are a professional editor. Your goal is to extract structured data from the text.\n"
            f"Context (Topic): {topic.title}\n"
            "IMPORTANT: ALWAYS use Russian language for the title, content, and tags.\n"
            "Task:\n"
            "1. 'title': Create a short, descriptive emoji title in Russian (max 5-7 words).\n"
            "2. 'content': Create a concise summary (caption) of the note in Russian. Fix grammar, remove redundancy.\n"
            "3. 'tags': Extract key tags (hashtags) in Russian.\n\n"
            "Return JSON only: {\"title\": \"...\", \"content\": \"...\", \"tags\": [\"#tag1\", ...]}"
        )

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": note_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            content = response.choices[0].message.content
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
            logger.error(f"Error rendering note: {e}")
            return RenderedNote(title="Заметка", content=note_text, tags=[])

    async def transcribe_voice(self, audio_data: bytes) -> str:
        """Transcribe using Whisper API."""
        # TODO: Implement Whisper API call later
        return ""
