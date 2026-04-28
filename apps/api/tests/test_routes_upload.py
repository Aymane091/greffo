import struct
import time
import wave
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.models.transcription_segment import TranscriptionSegment
from src.models.user import User
from src.services.storage_token import generate_upload_token, verify_upload_token
from src.storage.local import LocalStorageBackend
from src.workers import _run_pipeline


def _h(org_id: str, user_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"X-Org-Id": org_id}
    if user_id is not None:
        headers["X-User-Id"] = user_id
    return headers


def _make_wav_bytes(duration_s: float = 0.1) -> bytes:
    """Generate a minimal valid WAV file in memory."""
    sample_rate = 8000
    num_samples = int(sample_rate * duration_s)
    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


async def _create_tr_fixtures(
    db_session: AsyncSession,
) -> tuple[Organization, User, Case, Transcription]:
    org = Organization(name="Cabinet Upload Test")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="up@cabinet.fr", email_hash="hup", role="member")
    case = Case(organization_id=org.id, name="Dossier Upload")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="Audition Upload",
        status="draft",
        language="fr",
    )
    db_session.add(tr)
    await db_session.flush()
    return org, user, case, tr


# ---------------------------------------------------------------------------
# 1. upload-url returns a signed URL
# ---------------------------------------------------------------------------
async def test_upload_url_returns_signed_url(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)

    resp = await client.post(f"/api/v1/transcriptions/{tr.id}/upload-url", headers=_h(org.id))
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "expires_at" in data
    assert "/api/v1/storage/upload/" in data["upload_url"]

    # Token must be verifiable
    token = data["upload_url"].rsplit("/", 1)[-1]
    tr_id, org_id = verify_upload_token(token)
    assert tr_id == tr.id
    assert org_id == org.id


# ---------------------------------------------------------------------------
# 2. Full happy path: upload → confirm → pipeline → done + segments
# ---------------------------------------------------------------------------
async def test_upload_then_confirm_then_process(
    client: AsyncClient, db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)
    wav = _make_wav_bytes()

    # Get upload URL
    resp = await client.post(f"/api/v1/transcriptions/{tr.id}/upload-url", headers=_h(org.id))
    token = resp.json()["upload_url"].rsplit("/", 1)[-1]

    # Upload audio
    resp = await client.put(
        f"/api/v1/storage/upload/{token}",
        content=wav,
        headers={"Content-Type": "audio/wav", "Content-Length": str(len(wav))},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "wav"
    assert data["size_bytes"] == len(wav)

    # Confirm upload → status becomes 'queued'
    resp = await client.post(
        f"/api/v1/transcriptions/{tr.id}/confirm-upload", headers=_h(org.id)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"

    saved_tr_id = tr.id  # save before expire_all

    # Run pipeline directly (no ARQ / Redis needed in tests)
    await _run_pipeline(db_session, tmp_storage, saved_tr_id)

    # Verify final transcription state
    db_session.expire_all()
    result = await db_session.execute(
        select(Transcription).where(Transcription.id == saved_tr_id)
    )
    tr_final = result.scalar_one()
    assert tr_final.status == "done"
    assert tr_final.progress_pct == 100
    assert tr_final.processing_started_at is not None
    assert tr_final.processing_ended_at is not None

    # Verify stub segments were created
    seg_result = await db_session.execute(
        select(TranscriptionSegment)
        .where(TranscriptionSegment.transcription_id == saved_tr_id)
        .order_by(TranscriptionSegment.segment_index)
    )
    segments = seg_result.scalars().all()
    assert len(segments) == 10
    assert segments[0].speaker == "SPEAKER_00"
    assert segments[1].speaker == "SPEAKER_01"


# ---------------------------------------------------------------------------
# 3. Invalid MIME type → 415
# ---------------------------------------------------------------------------
async def test_upload_invalid_mime(
    client: AsyncClient, db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)

    resp = await client.post(f"/api/v1/transcriptions/{tr.id}/upload-url", headers=_h(org.id))
    token = resp.json()["upload_url"].rsplit("/", 1)[-1]

    # Send plain text — python-magic detects as text/plain
    resp = await client.put(
        f"/api/v1/storage/upload/{token}",
        content=b"This is not audio data at all.",
        headers={"Content-Type": "audio/mpeg", "Content-Length": "30"},
    )
    assert resp.status_code == 415

    # File must NOT be in storage
    assert not await tmp_storage.exists(f"audio/{tr.id}")


# ---------------------------------------------------------------------------
# 4. File too large → 413 (via Content-Length header)
# ---------------------------------------------------------------------------
async def test_upload_too_large(
    client: AsyncClient, db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)

    resp = await client.post(f"/api/v1/transcriptions/{tr.id}/upload-url", headers=_h(org.id))
    token = resp.json()["upload_url"].rsplit("/", 1)[-1]

    oversized_length = str(600 * 1024 * 1024)  # 600 MB declared in header
    resp = await client.put(
        f"/api/v1/storage/upload/{token}",
        content=b"x",  # tiny body — server rejects before reading
        headers={"Content-Type": "audio/wav", "Content-Length": oversized_length},
    )
    assert resp.status_code == 413

    # No partial file in storage
    assert not await tmp_storage.exists(f"audio/{tr.id}")


# ---------------------------------------------------------------------------
# 5. Expired signed URL → 401
# ---------------------------------------------------------------------------
async def test_signed_url_expires(
    client: AsyncClient, db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)

    # Forge a token with exp in the past
    import hashlib
    import hmac

    from src.config import settings

    exp = int(time.time()) - 1  # already expired
    message = f"{tr.id}|{org.id}|{exp}"
    sig = hmac.new(
        settings.storage_secret.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    expired_token = f"{tr.id}.{org.id}.{exp}.{sig}"

    resp = await client.put(
        f"/api/v1/storage/upload/{expired_token}",
        content=_make_wav_bytes(),
        headers={"Content-Type": "audio/wav"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "upload_url_expired"


# ---------------------------------------------------------------------------
# 6. Confirm without uploading first → 404
# ---------------------------------------------------------------------------
async def test_confirm_upload_without_file(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org, user, case, tr = await _create_tr_fixtures(db_session)

    resp = await client.post(
        f"/api/v1/transcriptions/{tr.id}/confirm-upload", headers=_h(org.id)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "audio_not_uploaded"


# ---------------------------------------------------------------------------
# 7. Status transitions are audited during pipeline
# ---------------------------------------------------------------------------
async def test_status_transitions_are_audited(
    db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org = Organization(name="Cabinet Audit Pipeline")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="aud@cabinet.fr", email_hash="haud", role="member")
    case = Case(organization_id=org.id, name="Dossier Audit")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="Audit Transcription",
        status="queued",
        language="fr",
        audio_s3_key=f"audio/{org.id}/fake.wav",  # pre-set so pipeline doesn't fail
    )
    db_session.add(tr)
    await db_session.flush()

    # Storage: create a dummy file so exists() returns True
    await tmp_storage.upload(f"audio/{org.id}/fake.wav", b"fake", "audio/wav")

    with patch("src.workers.log_action", new_callable=AsyncMock) as mock_log:
        await _run_pipeline(db_session, tmp_storage, tr.id)
        actions = [call.args[0] for call in mock_log.call_args_list]

    assert actions == ["PROCESSING", "DONE"]


# ---------------------------------------------------------------------------
# 8. Pipeline failure → status='failed'
# ---------------------------------------------------------------------------
async def test_failed_transcription(
    db_session: AsyncSession, tmp_storage: LocalStorageBackend, monkeypatch: pytest.MonkeyPatch
) -> None:
    org = Organization(name="Cabinet Fail Pipeline")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="fail@cabinet.fr", email_hash="hfail", role="member")
    case = Case(organization_id=org.id, name="Dossier Fail")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="Fail Transcription",
        status="queued",
        language="fr",
        audio_s3_key="audio/fake-fail.wav",
    )
    db_session.add(tr)
    await db_session.flush()

    saved_tr_id = tr.id  # save before expire_all

    # Create the dummy audio file so the exists() check passes
    await tmp_storage.upload("audio/fake-fail.wav", b"fake-wav-bytes", "audio/wav")

    # Inject a provider that raises a TranscriptionError to trigger the failure path
    from src.services.transcription import TranscriptionError, TranscriptionProvider

    class _FailProvider(TranscriptionProvider):
        async def transcribe(self, audio_bytes: bytes, language: str):
            raise TranscriptionError("AUDIO_INVALID", "simulated provider failure")

    monkeypatch.setattr("src.workers.get_provider", lambda: _FailProvider())

    await _run_pipeline(db_session, tmp_storage, saved_tr_id)

    db_session.expire_all()
    result = await db_session.execute(select(Transcription).where(Transcription.id == saved_tr_id))
    tr_final = result.scalar_one()
    assert tr_final.status == "failed"
    assert tr_final.error_code == "AUDIO_INVALID"


# ---------------------------------------------------------------------------
# 9. Tenant isolation: org B cannot access org A's upload URL
# ---------------------------------------------------------------------------
async def test_tenant_isolation_upload(
    client: AsyncClient, db_session: AsyncSession, tmp_storage: LocalStorageBackend
) -> None:
    org_a = Organization(name="Cabinet Iso A Upload")
    org_b = Organization(name="Cabinet Iso B Upload")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    user_a = User(
        organization_id=org_a.id, email="isoa@cabinet.fr", email_hash="hisoa", role="member"
    )
    case_a = Case(organization_id=org_a.id, name="Dossier Iso A")
    db_session.add_all([user_a, case_a])
    await db_session.flush()
    tr_a = Transcription(
        organization_id=org_a.id,
        user_id=user_a.id,
        case_id=case_a.id,
        title="Tr Iso A",
        status="draft",
        language="fr",
    )
    db_session.add(tr_a)
    await db_session.flush()

    # Org A gets upload URL
    resp = await client.post(
        f"/api/v1/transcriptions/{tr_a.id}/upload-url", headers=_h(org_a.id)
    )
    assert resp.status_code == 200
    token = resp.json()["upload_url"].rsplit("/", 1)[-1]

    # Org B tries to use it — the token encodes org_a.id, so the transcription
    # lookup fails (org_id mismatch) → 404, not the audio for org B
    # We verify the token itself is valid but the transcription won't be found
    # because the org check in the route fails.
    # (We can't test this via the X-Org-Id header since the token carries the org_id itself)
    # Instead, verify that org B cannot generate an upload URL for org A's transcription:
    resp_b = await client.post(
        f"/api/v1/transcriptions/{tr_a.id}/upload-url", headers=_h(org_b.id)
    )
    assert resp_b.status_code == 404  # transcription not found for org_b
