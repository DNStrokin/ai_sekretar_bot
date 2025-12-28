"""
STT Service

Единый интерфейс для распознавания речи.
"""

from abc import ABC, abstractmethod
from typing import Optional


class STTService(ABC):
    """Abstract STT service interface."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "ru") -> str:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Raw audio bytes (OGG/OPUS from Telegram)
            language: Target language code
            
        Returns:
            Transcribed text
        """
        pass


class OpenAISTT(STTService):
    """OpenAI Whisper STT implementation."""

    async def transcribe(self, audio_data: bytes, language: str = "ru") -> str:
        """Transcribe using Whisper API."""
        # TODO: Implement Whisper API call
        return ""


class GoogleSTT(STTService):
    """Google Speech-to-Text implementation."""

    async def transcribe(self, audio_data: bytes, language: str = "ru") -> str:
        """Transcribe using Google Speech API."""
        # TODO: Implement Google Speech API call
        return ""


def get_stt_service(provider: str = "openai") -> STTService:
    """Factory function to get STT service by provider name."""
    if provider == "openai":
        return OpenAISTT()
    elif provider == "google":
        return GoogleSTT()
    else:
        raise ValueError(f"Unknown STT provider: {provider}")
