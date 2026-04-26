from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.organization import Organization
from src.models.user import User


async def test_create_organization_returns_201(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post(
        "/api/v1/organizations",
        json={"name": "Cabinet Lefebvre"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cabinet Lefebvre"
    assert data["slug"] == "cabinet-lefebvre"
    assert len(data["id"]) == 26
    assert data["plan"] is None
    assert data["audio_retention_days"] == 30


async def test_create_organization_invalid_siret_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    response = await client.post(
        "/api/v1/organizations",
        json={"name": "Cabinet Test", "siret": "1234"},
    )
    assert response.status_code == 422


async def test_get_me_without_header_returns_401(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.get("/api/v1/organizations/me")
    assert response.status_code == 401


async def test_get_me_with_valid_org_returns_200(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Bernard")
    db_session.add(org)
    await db_session.flush()

    response = await client.get(
        "/api/v1/organizations/me",
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == org.id
    assert data["name"] == "Cabinet Bernard"


async def test_get_me_with_unknown_org_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.get(
        "/api/v1/organizations/me",
        headers={"X-Org-Id": "01DOESNOTEXIST00000000000X"},
    )
    assert response.status_code == 404


async def test_patch_me_updates_name_and_address(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Ancien", plan="starter", quota_minutes=100)
    db_session.add(org)
    await db_session.flush()

    response = await client.patch(
        "/api/v1/organizations/me",
        json={"name": "Cabinet Nouveau", "address": "12 rue de la Paix, Paris"},
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Cabinet Nouveau"
    assert data["address"] == "12 rue de la Paix, Paris"
    assert data["plan"] == "starter"
    assert data["quota_minutes"] == 100


async def test_patch_me_ignores_plan_field(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Plan Test", plan="starter")
    db_session.add(org)
    await db_session.flush()

    response = await client.patch(
        "/api/v1/organizations/me",
        json={"name": "Cabinet Plan Test", "plan": "enterprise"},
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    assert response.json()["plan"] == "starter"


async def test_tenant_isolation_users_list(client: AsyncClient, db_session: AsyncSession) -> None:
    org_a = Organization(name="Cabinet Isolation A")
    org_b = Organization(name="Cabinet Isolation B")
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    user_a = User(
        organization_id=org_a.id,
        email="user@cabinet-isolation-a.fr",
        email_hash="hash_isolation_a",
        role="member",
    )
    db_session.add(user_a)
    await db_session.flush()

    response = await client.get(
        "/api/v1/organizations/me/users",
        headers={"X-Org-Id": org_b.id},
    )
    assert response.status_code == 200
    returned_ids = [u["id"] for u in response.json()]
    assert user_a.id not in returned_ids
