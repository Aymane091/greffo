from src.services.transcription import (
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptionSegmentResult,
)

_STUB_SEGMENTS: list[tuple[float, float, str, str, float]] = [
    (0.0, 3.5, "SPEAKER_00", "Monsieur le Président, la séance est ouverte.", 0.92),
    (4.0, 7.2, "SPEAKER_01", "Maître, pouvez-vous présenter votre client ?", 0.89),
    (7.8, 12.1, "SPEAKER_00", "Bien entendu. Mon client, Monsieur Martin, est présent à l'audience.", 0.94),
    (12.5, 16.0, "SPEAKER_01", "Monsieur Martin, vous êtes bien prévenu des faits qui vous sont reprochés ?", 0.91),
    (16.8, 19.3, "SPEAKER_00", "Oui, Monsieur le Président. Je reconnais les faits.", 0.88),
    (20.0, 24.5, "SPEAKER_01", "Maître, quels sont les éléments à charge que vous souhaitez contester ?", 0.93),
    (25.0, 30.2, "SPEAKER_00", "Nous contestons la valeur probante du rapport d'expertise versé au dossier.", 0.87),
    (31.0, 35.8, "SPEAKER_01", "L'expert sera entendu à l'audience de renvoi. Avez-vous des observations ?", 0.90),
    (36.5, 41.0, "SPEAKER_00", "Nous demandons le renvoi de l'affaire pour permettre une contre-expertise.", 0.85),
    (42.0, 45.5, "SPEAKER_01", "La cour se retire pour délibérer. L'audience reprend dans trente minutes.", 0.96),
]


class StubProvider(TranscriptionProvider):
    """Deterministic stub for local dev and tests — no external calls, no sleep."""

    async def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        segments = [
            TranscriptionSegmentResult(
                start_s=start_s,
                end_s=end_s,
                speaker=speaker,
                text=text,
                confidence=confidence,
            )
            for start_s, end_s, speaker, text, confidence in _STUB_SEGMENTS
        ]
        duration_s = max(seg.end_s for seg in segments) if segments else 0.0
        return TranscriptionResult(
            segments=segments,
            language_detected=language,
            duration_s=duration_s,
        )
