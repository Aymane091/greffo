import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from src.models.user import User


async def test_insert_read_user(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Dupont")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="avocat@cabinet-dupont.fr",
        email_hash="sha256_placeholder",
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()

    assert fetched.email == "avocat@cabinet-dupont.fr"
    assert fetched.role == "owner"
    assert fetched.mfa_enabled is False
    assert fetched.organization_id == org.id
    assert fetched.deleted_at is None
    assert len(fetched.id) == 26


async def test_role_check_constraint(db_session: AsyncSession) -> None:
    from sqlalchemy.exc import IntegrityError

    org = Organization(name="Cabinet Test")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="x@x.fr",
        email_hash="h",
        role="superadmin",  # invalide
    )
    db_session.add(user)

    with pytest.raises(IntegrityError, match="users_role_check"):
        await db_session.flush()
