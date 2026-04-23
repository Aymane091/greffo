from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.models.user import User


async def test_insert_read_transcription(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Lefebvre")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="lefebvre@cabinet.fr",
        email_hash="h2",
        role="member",
    )
    db_session.add(user)
    await db_session.flush()

    case = Case(
        organization_id=org.id,
        name="Affaire Moreau",
        created_by=user.id,
    )
    db_session.add(case)
    await db_session.flush()

    tr = Transcription(
        organization_id=org.id,
        case_id=case.id,
        user_id=user.id,
        title="Audition du 23 avril 2026",
        audio_format="mp3",
        audio_duration_s=3600,
        audio_size_bytes=52_428_800,
    )
    db_session.add(tr)
    await db_session.flush()

    result = await db_session.execute(select(Transcription).where(Transcription.id == tr.id))
    fetched = result.scalar_one()

    assert fetched.title == "Audition du 23 avril 2026"
    assert fetched.status == "queued"
    assert fetched.language == "fr"
    assert fetched.audio_format == "mp3"
    assert fetched.audio_duration_s == 3600
    assert fetched.audio_size_bytes == 52_428_800
    assert fetched.organization_id == org.id
    assert fetched.case_id == case.id
    assert fetched.user_id == user.id
    assert fetched.processing_started_at is None
    assert fetched.deleted_at is None
    assert len(fetched.id) == 26


async def test_transcription_without_case(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Seul")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="seul@cabinet.fr",
        email_hash="h3",
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()

    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        audio_format="wav",
    )
    db_session.add(tr)
    await db_session.flush()

    result = await db_session.execute(select(Transcription).where(Transcription.id == tr.id))
    fetched = result.scalar_one()

    assert fetched.case_id is None
    assert fetched.status == "queued"
