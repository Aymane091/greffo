from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.user import User


async def test_insert_read_case(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Martin")
    db_session.add(org)
    await db_session.flush()

    user = User(
        organization_id=org.id,
        email="martin@cabinet.fr",
        email_hash="h1",
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()

    case = Case(
        organization_id=org.id,
        name="Affaire Durand c/ État",
        reference="2026-PEN-001",
        created_by=user.id,
    )
    db_session.add(case)
    await db_session.flush()

    result = await db_session.execute(select(Case).where(Case.id == case.id))
    fetched = result.scalar_one()

    assert fetched.name == "Affaire Durand c/ État"
    assert fetched.reference == "2026-PEN-001"
    assert fetched.organization_id == org.id
    assert fetched.created_by == user.id
    assert fetched.archived_at is None
    assert fetched.deleted_at is None
    assert len(fetched.id) == 26


async def test_case_without_user(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Solo")
    db_session.add(org)
    await db_session.flush()

    case = Case(organization_id=org.id, name="Dossier sans auteur")
    db_session.add(case)
    await db_session.flush()

    result = await db_session.execute(select(Case).where(Case.id == case.id))
    fetched = result.scalar_one()

    assert fetched.created_by is None
