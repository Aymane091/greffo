from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization


async def test_insert_read_organization(db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Dupont", slug="cabinet-dupont")
    db_session.add(org)
    await db_session.flush()

    result = await db_session.execute(
        select(Organization).where(Organization.id == org.id)
    )
    fetched = result.scalar_one()

    assert fetched.name == "Cabinet Dupont"
    assert fetched.slug == "cabinet-dupont"
    assert fetched.id is not None
    assert len(fetched.id) == 26  # longueur d'un ULID
    assert fetched.audio_retention_days == 30
    assert fetched.dpa_signed_at is None
    assert fetched.deleted_at is None
