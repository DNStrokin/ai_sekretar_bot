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
            genai.configure(api_key=self.api_key)
            # Используем gemini-3-flash-preview по запросу пользователя
            try:
                self.model = genai.GenerativeModel('gemini-3-flash-preview')
            except Exception:
                # Fallback
                self.model = genai.GenerativeModel('gemini-flash-latest') 

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
            "Task: Analyze the user's note. Identify ALL topics that might be relevant.\n"
            "Assign a confidence score (0.0 to 1.0) to each relevant topic.\n"
            "If the note is completely unrelated to any existing topic, include {\"id\": 0, \"confidence\": 1.0}.\n\n"
            "Return JSON only: {\"candidates\": [{\"id\": <topic_id>, \"confidence\": <score>}, ...]}"
        )
        
        # try:
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
        
        candidates = data.get("candidates", [])
        if not candidates:
             # Fallback logic if structure differs or empty
             old_id = data.get("id", 0)
             candidates = [{"id": old_id, "confidence": data.get("confidence", 1.0)}]

        # Sort by confidence desc
        candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # Filter invalid topics
        valid_candidates = [
            c for c in candidates 
            if c["id"] == 0 or any(t.topic_id == c["id"] for t in topics)
        ]
        
        if not valid_candidates:
            valid_candidates = [{"id": 0, "confidence": 1.0}]
            
        best = valid_candidates[0]
        
        return ClassificationResult(
            suggested_topic_id=best["id"],
            top_topics=[{"topic_id": c["id"], "confidence": c.get("confidence", 0.0)} for c in valid_candidates],
            need_new_topic=(best["id"] == 0)
        )

        # except Exception as e:
        #     logger.error(f"Error classifying note with Gemini: {e}")
        #     return ClassificationResult(suggested_topic_id=0, top_topics=[], need_new_topic=True)

    async def render_note(
        self,
        note_text: str,
        topic: TopicContext
    ) -> RenderedNote:
        """Format note using Gemini."""
        if not self.model:
             return RenderedNote(title="Заметка", content=note_text, tags=[])

        # Для работы с системой шаблонов нам нужны чистые данные
        # format_rules мы больше не передаем в промпт для стиля, 
        # так как стиль задается шаблоном в боте.
        
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

        # try:
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

        # except Exception as e:
        #     logger.error(f"Error rendering note with Gemini: {e}")
        #     return RenderedNote(title="Заметка", content=note_text, tags=[])

    async def transcribe_voice(self, audio_data: bytes) -> str:
        """Transcribe using Gemini (multimodal)."""
        # TODO: Implement Gemini audio transcription
        return ""
