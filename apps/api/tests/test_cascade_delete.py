import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.models.user import User


async def test_cascade_delete_org_removes_all_children(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Cascade")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="cascade@cabinet.fr",
        email_hash="hcascade",
        role="member",
    )
    db_session.add(user)
    await db_session.flush()

    case = Case(organization_id=org.id, name="Affaire Cascade", created_by=user.id)
    db_session.add(case)
    await db_session.flush()

    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        audio_format="mp3",
    )
    db_session.add(tr)
    await db_session.flush()

    org_id = org.id
    user_id = user.id
    case_id = case.id
    tr_id = tr.id

    await db_session.delete(org)
    await db_session.flush()
    db_session.expire_all()

    assert (await db_session.get(User, user_id)) is None
    assert (await db_session.get(Case, case_id)) is None
    assert (await db_session.get(Transcription, tr_id)) is None
    result = await db_session.execute(select(Organization).where(Organization.id == org_id))
    assert result.scalar_one_or_none() is None


async def test_insert_with_nonexistent_org_raises_integrity_error(db_session: AsyncSession) -> None:
    user = User(
        organization_id="01NONEXISTENTORGID000000XX",
        email="ghost@cabinet.fr",
        email_hash="hghost",
        role="member",
    )
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()
