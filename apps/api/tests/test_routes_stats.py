from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.models.user import User


async def _seed(
    db: AsyncSession,
    name: str = "Cabinet Stats",
) -> tuple[Organization, User]:
    org = Organization(name=name)
    db.add(org)
    await db.flush()
    user = User(organization_id=org.id, email=f"stats-{org.id}@test.fr",
                email_hash=f"h{org.id}", role="owner")
    db.add(user)
    await db.flush()
    return org, user


async def test_stats_dashboard_empty_org(client: AsyncClient, db_session: AsyncSession) -> None:
    """An org with no data returns all-zero stats."""
    org, _ = await _seed(db_session, "Empty Org Stats")

    resp = await client.get("/api/v1/stats/dashboard", headers={"X-Org-Id": org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_cases"] == 0
    assert data["archived_cases"] == 0
    assert data["transcriptions_this_month"] == 0
    assert data["total_audio_duration_seconds"] == 0.0
    assert data["status_breakdown"] == {"done": 0, "processing": 0, "failed": 0, "queued": 0}


async def test_stats_dashboard_counts(client: AsyncClient, db_session: AsyncSession) -> None:
    """Correct counts for active, archived cases and transcriptions."""
    org, user = await _seed(db_session, "Cabinet Counts")

    # 2 active cases, 1 archived
    c1 = Case(organization_id=org.id, name="Active 1")
    c2 = Case(organization_id=org.id, name="Active 2")
    c3 = Case(organization_id=org.id, name="Archived 1",
              archived_at=datetime.now(timezone.utc))
    db_session.add_all([c1, c2, c3])

    # 2 transcriptions: 1 done (120s), 1 processing
    t1 = Transcription(organization_id=org.id, user_id=user.id, case_id=c1.id,
                       title="TR1", status="done", language="fr",
                       audio_duration_s=120, audio_s3_key="k1")
    t2 = Transcription(organization_id=org.id, user_id=user.id, case_id=c1.id,
                       title="TR2", status="processing", language="fr",
                       audio_s3_key="k2")
    db_session.add_all([t1, t2])
    await db_session.flush()

    resp = await client.get("/api/v1/stats/dashboard", headers={"X-Org-Id": org.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_cases"] == 2
    assert data["archived_cases"] == 1
    assert data["transcriptions_this_month"] == 2
    assert data["total_audio_duration_seconds"] == 120.0
    assert data["status_breakdown"]["done"] == 1
    assert data["status_breakdown"]["processing"] == 1


async def test_stats_dashboard_multi_tenancy(client: AsyncClient, db_session: AsyncSession) -> None:
    """Org A cannot see Org B data."""
    org_a, user_a = await _seed(db_session, "Org A Stats")
    org_b, user_b = await _seed(db_session, "Org B Stats")

    # Org B has 5 cases and 3 transcriptions
    for i in range(5):
        db_session.add(Case(organization_id=org_b.id, name=f"B-Case {i}"))
    await db_session.flush()
    for i in range(3):
        db_session.add(Transcription(
            organization_id=org_b.id, user_id=user_b.id,
            title=f"B-TR{i}", status="done", language="fr",
            audio_duration_s=60, audio_s3_key=f"kb{i}",
        ))
    await db_session.flush()

    # Org A sees only its own (empty) data
    resp = await client.get("/api/v1/stats/dashboard", headers={"X-Org-Id": org_a.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_cases"] == 0
    assert data["transcriptions_this_month"] == 0


async def test_stats_dashboard_requires_org_header(client: AsyncClient) -> None:
    """Missing X-Org-Id returns 401."""
    resp = await client.get("/api/v1/stats/dashboard")
    assert resp.status_code == 401
