from abc import ABC, abstractmethod

from pydantic import BaseModel


class TranscriptionSegmentResult(BaseModel):
    start_s: float
    end_s: float
    speaker: str
    text: str
    confidence: float


class TranscriptionResult(BaseModel):
    segments: list[TranscriptionSegmentResult]
    language_detected: str
    duration_s: float


class TranscriptionError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult: ...


def get_provider() -> TranscriptionProvider:
    from src.config import settings

    if settings.transcription_provider == "stub":
        from src.services.transcription.stub import StubProvider

        return StubProvider()

    if settings.transcription_provider == "gladia":
        from src.services.transcription.gladia import GladiaProvider

        return GladiaProvider(
            api_key=settings.gladia_api_key or "",
            base_url=settings.gladia_base_url,
            timeout_s=settings.transcription_timeout_seconds,
        )

    raise ValueError(f"Unknown transcription provider: {settings.transcription_provider}")
