"""
Tests for the transcription provider abstraction and GladiaProvider.
All Gladia HTTP calls are intercepted by respx — no real network traffic.
"""
import struct
import wave
from io import BytesIO

import httpx
import pytest
import respx
from pydantic import ValidationError

from src.services.transcription import (
    TranscriptionError,
    TranscriptionResult,
    get_provider,
)
from src.services.transcription.gladia import GladiaProvider
from src.services.transcription.stub import StubProvider

_BASE = "https://api.gladia.io"

# ---------------------------------------------------------------------------
# Minimal helpers
# ---------------------------------------------------------------------------

def _wav_bytes() -> bytes:
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(struct.pack("<80h", *([0] * 80)))
    return buf.getvalue()


_UPLOAD_OK = {
    "audio_url": f"{_BASE}/file/abc123",
    "audio_metadata": {"id": "abc123", "audio_duration": 120.0},
}

_JOB_STARTED = {"id": "job-xyz", "result_url": f"{_BASE}/v2/pre-recorded/job-xyz"}

_JOB_DONE = {
    "status": "done",
    "file": {"duration": 120.0},
    "result": {
        "transcription": {
            "languages": ["fr"],
            "utterances": [
                {
                    "start": 0.5,
                    "end": 3.2,
                    "confidence": 0.91,
                    "text": "Monsieur le Président, la séance est ouverte.",
                    "speaker": "speaker_1",
                },
                {
                    "start": 4.0,
                    "end": 7.0,
                    "confidence": 0.88,
                    "text": "Maître, présentez votre client.",
                    "speaker": "speaker_2",
                },
                {
                    "start": 8.0,
                    "end": 10.0,
                    "confidence": 0.85,
                    "text": "Mon client reconnaît les faits.",
                    "speaker": "speaker_1",
                },
            ],
        }
    },
}

_JOB_ERROR = {"status": "error", "error_code": "INVALID_AUDIO_FILE"}


# ---------------------------------------------------------------------------
# 1. Factory returns StubProvider when provider=stub
# ---------------------------------------------------------------------------
def test_provider_factory_returns_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.config

    monkeypatch.setattr(src.config.settings, "transcription_provider", "stub")
    provider = get_provider()
    assert isinstance(provider, StubProvider)


# ---------------------------------------------------------------------------
# 2. Factory returns GladiaProvider when provider=gladia
# ---------------------------------------------------------------------------
def test_provider_factory_returns_gladia(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.config

    monkeypatch.setattr(src.config.settings, "transcription_provider", "gladia")
    monkeypatch.setattr(src.config.settings, "gladia_api_key", "test-key")
    monkeypatch.setattr(src.config.settings, "gladia_base_url", _BASE)
    monkeypatch.setattr(src.config.settings, "transcription_timeout_seconds", 1800)
    provider = get_provider()
    assert isinstance(provider, GladiaProvider)


# ---------------------------------------------------------------------------
# 3. Gladia happy path — upload + start job + poll done → correct mapping
# ---------------------------------------------------------------------------
@respx.mock
async def test_gladia_happy_path() -> None:
    respx.post(f"{_BASE}/v2/upload").mock(return_value=httpx.Response(200, json=_UPLOAD_OK))
    respx.post(f"{_BASE}/v2/pre-recorded").mock(
        return_value=httpx.Response(201, json=_JOB_STARTED)
    )
    respx.get(f"{_BASE}/v2/pre-recorded/job-xyz").mock(
        return_value=httpx.Response(200, json=_JOB_DONE)
    )

    provider = GladiaProvider(api_key="test-key", base_url=_BASE)
    result = await provider.transcribe(_wav_bytes(), "fr")

    assert isinstance(result, TranscriptionResult)
    assert result.language_detected == "fr"
    assert result.duration_s == 120.0
    assert len(result.segments) == 3

    # Speaker normalisation: speaker_1 → SPEAKER_00, speaker_2 → SPEAKER_01
    assert result.segments[0].speaker == "SPEAKER_00"
    assert result.segments[1].speaker == "SPEAKER_01"
    assert result.segments[2].speaker == "SPEAKER_00"  # same speaker_1

    assert result.segments[0].start_s == 0.5
    assert result.segments[0].end_s == 3.2
    assert result.segments[0].confidence == pytest.approx(0.91)


# ---------------------------------------------------------------------------
# 4. 401 on upload → AUTH_ERROR
# ---------------------------------------------------------------------------
@respx.mock
async def test_gladia_auth_error() -> None:
    respx.post(f"{_BASE}/v2/upload").mock(return_value=httpx.Response(401, json={}))

    provider = GladiaProvider(api_key="bad-key", base_url=_BASE)
    with pytest.raises(TranscriptionError) as exc_info:
        await provider.transcribe(_wav_bytes(), "fr")

    assert exc_info.value.error_code == "AUTH_ERROR"


# ---------------------------------------------------------------------------
# 5. 429 on job start → retry → success
# ---------------------------------------------------------------------------
@respx.mock
async def test_gladia_rate_limit_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    respx.post(f"{_BASE}/v2/upload").mock(return_value=httpx.Response(200, json=_UPLOAD_OK))
    respx.post(f"{_BASE}/v2/pre-recorded").mock(
        side_effect=[
            httpx.Response(429, json={}),
            httpx.Response(201, json=_JOB_STARTED),
        ]
    )
    respx.get(f"{_BASE}/v2/pre-recorded/job-xyz").mock(
        return_value=httpx.Response(200, json=_JOB_DONE)
    )

    provider = GladiaProvider(api_key="test-key", base_url=_BASE)
    result = await provider.transcribe(_wav_bytes(), "fr")

    assert result.language_detected == "fr"
    assert len(result.segments) == 3


# ---------------------------------------------------------------------------
# 6. Polling always returns "processing" → TIMEOUT
# ---------------------------------------------------------------------------
@respx.mock
async def test_gladia_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    # audio_duration=0 so the adaptive timeout falls back to self._timeout_s (=0),
    # not the 600s short-audio override.
    _upload_zero_duration = {
        "audio_url": f"{_BASE}/file/abc123",
        "audio_metadata": {"id": "abc123", "audio_duration": 0},
    }
    respx.post(f"{_BASE}/v2/upload").mock(
        return_value=httpx.Response(200, json=_upload_zero_duration)
    )
    respx.post(f"{_BASE}/v2/pre-recorded").mock(
        return_value=httpx.Response(201, json=_JOB_STARTED)
    )
    respx.get(f"{_BASE}/v2/pre-recorded/job-xyz").mock(
        return_value=httpx.Response(200, json={"status": "processing"})
    )

    # timeout_s=0 → deadline already expired after the first poll returns "processing"
    provider = GladiaProvider(api_key="test-key", base_url=_BASE, timeout_s=0)
    with pytest.raises(TranscriptionError) as exc_info:
        await provider.transcribe(_wav_bytes(), "fr")

    assert exc_info.value.error_code == "TIMEOUT"


# ---------------------------------------------------------------------------
# 7. Gladia returns status=error → AUDIO_INVALID
# ---------------------------------------------------------------------------
@respx.mock
async def test_gladia_audio_invalid() -> None:
    respx.post(f"{_BASE}/v2/upload").mock(return_value=httpx.Response(200, json=_UPLOAD_OK))
    respx.post(f"{_BASE}/v2/pre-recorded").mock(
        return_value=httpx.Response(201, json=_JOB_STARTED)
    )
    respx.get(f"{_BASE}/v2/pre-recorded/job-xyz").mock(
        return_value=httpx.Response(200, json=_JOB_ERROR)
    )

    provider = GladiaProvider(api_key="test-key", base_url=_BASE)
    with pytest.raises(TranscriptionError) as exc_info:
        await provider.transcribe(_wav_bytes(), "fr")

    assert exc_info.value.error_code == "AUDIO_INVALID"


# ---------------------------------------------------------------------------
# 8. _run_pipeline uses get_provider() factory
# ---------------------------------------------------------------------------
async def test_pipeline_uses_provider_factory(
    db_session, tmp_storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.models.case import Case
    from src.models.organization import Organization
    from src.models.transcription import Transcription
    from src.models.transcription_segment import TranscriptionSegment
    from src.models.user import User
    from src.workers import _run_pipeline
    from sqlalchemy import select

    org = Organization(name="Cabinet Provider Test")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="prov@cabinet.fr", email_hash="hprov", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier Provider")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="Test Provider",
        status="queued",
        language="fr",
        audio_s3_key="audio/provider-test.wav",
    )
    db_session.add(tr)
    await db_session.flush()

    await tmp_storage.upload("audio/provider-test.wav", _wav_bytes(), "audio/wav")

    # Inject a custom provider via get_provider factory
    from src.services.transcription import TranscriptionProvider, TranscriptionResult, TranscriptionSegmentResult

    class _CustomProvider(TranscriptionProvider):
        called = False

        async def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
            _CustomProvider.called = True
            return TranscriptionResult(
                segments=[
                    TranscriptionSegmentResult(
                        start_s=0.0, end_s=2.0, speaker="SPEAKER_00",
                        text="Test segment.", confidence=0.99,
                    )
                ],
                language_detected="fr",
                duration_s=2.0,
            )

    monkeypatch.setattr("src.workers.get_provider", lambda: _CustomProvider())

    saved_id = tr.id
    await _run_pipeline(db_session, tmp_storage, saved_id)

    assert _CustomProvider.called

    db_session.expire_all()
    tr_done = (
        await db_session.execute(select(Transcription).where(Transcription.id == saved_id))
    ).scalar_one()
    assert tr_done.status == "done"

    segs = (
        await db_session.execute(
            select(TranscriptionSegment)
            .where(TranscriptionSegment.transcription_id == saved_id)
        )
    ).scalars().all()
    assert len(segs) == 1
    assert segs[0].speaker == "SPEAKER_00"


# ---------------------------------------------------------------------------
# 9. provider=gladia + empty key → ValidationError at Settings instantiation
# ---------------------------------------------------------------------------
def test_gladia_empty_key_raises_at_startup() -> None:
    from src.config import Settings

    with pytest.raises(ValidationError, match="GLADIA_API_KEY"):
        Settings(transcription_provider="gladia", gladia_api_key="")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _no_sleep(_: float) -> None:
    """Drop-in for asyncio.sleep that returns immediately."""
