from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization


async def test_create_case_returns_201(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Création Case")
    db_session.add(org)
    await db_session.flush()

    response = await client.post(
        "/api/v1/cases",
        json={"name": "Affaire Martin"},
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Affaire Martin"
    assert len(data["id"]) == 26
    assert data["archived_at"] is None
    assert data["organization_id"] == org.id


async def test_create_case_missing_name_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet 422 Case")
    db_session.add(org)
    await db_session.flush()

    response = await client.post(
        "/api/v1/cases",
        json={},
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 422


async def test_list_cases_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Pagination Cases")
    db_session.add(org)
    await db_session.flush()

    for i in range(3):
        db_session.add(Case(organization_id=org.id, name=f"Affaire {i}"))
    await db_session.flush()

    response = await client.get(
        "/api/v1/cases?page=1&size=2",
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2
    assert data["page"] == 1


async def test_list_cases_archived_filter_states(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Archive Filter")
    db_session.add(org)
    await db_session.flush()

    active_case = Case(organization_id=org.id, name="Case Active")
    archived_case = Case(organization_id=org.id, name="Case Archivée")
    db_session.add_all([active_case, archived_case])
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/cases/{archived_case.id}/archive",
        headers={"X-Org-Id": org.id},
    )
    assert resp.status_code == 200

    # archived=false (défaut) → seulement active
    resp = await client.get("/api/v1/cases", headers={"X-Org-Id": org.id})
    ids = [c["id"] for c in resp.json()["items"]]
    assert active_case.id in ids
    assert archived_case.id not in ids

    # archived=true → seulement archivée
    resp = await client.get("/api/v1/cases?archived=true", headers={"X-Org-Id": org.id})
    ids = [c["id"] for c in resp.json()["items"]]
    assert archived_case.id in ids
    assert active_case.id not in ids

    # archived=all → les deux
    resp = await client.get("/api/v1/cases?archived=all", headers={"X-Org-Id": org.id})
    ids = [c["id"] for c in resp.json()["items"]]
    assert active_case.id in ids
    assert archived_case.id in ids


async def test_get_case_detail_returns_200(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Get Case")
    db_session.add(org)
    await db_session.flush()
    case = Case(organization_id=org.id, name="Affaire Dupont")
    db_session.add(case)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/cases/{case.id}",
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Affaire Dupont"


async def test_get_case_from_other_org_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_a = Organization(name="Cabinet A Case Iso")
    org_b = Organization(name="Cabinet B Case Iso")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    case_a = Case(organization_id=org_a.id, name="Dossier Secret A")
    db_session.add(case_a)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/cases/{case_a.id}",
        headers={"X-Org-Id": org_b.id},
    )
    assert response.status_code == 404


async def test_patch_case_partial_update(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Patch Case")
    db_session.add(org)
    await db_session.flush()
    case = Case(organization_id=org.id, name="Nom Original")
    db_session.add(case)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/cases/{case.id}",
        json={"reference": "REF-2026-001"},
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reference"] == "REF-2026-001"
    assert data["name"] == "Nom Original"


async def test_archive_case(client: AsyncClient, db_session: AsyncSession) -> None:
    org = Organization(name="Cabinet Archive Case")
    db_session.add(org)
    await db_session.flush()
    case = Case(organization_id=org.id, name="À Archiver")
    db_session.add(case)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/cases/{case.id}/archive",
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


async def test_soft_delete_case_returns_204_and_hides_from_list(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Delete Case")
    db_session.add(org)
    await db_session.flush()
    case = Case(organization_id=org.id, name="À Supprimer")
    db_session.add(case)
    await db_session.flush()

    saved_case_id = case.id  # sauvegarder avant expire_all
    response = await client.delete(
        f"/api/v1/cases/{saved_case_id}",
        headers={"X-Org-Id": org.id},
    )
    assert response.status_code == 204

    list_resp = await client.get("/api/v1/cases", headers={"X-Org-Id": org.id})
    ids = [c["id"] for c in list_resp.json()["items"]]
    assert saved_case_id not in ids

    db_session.expire_all()
    result = await db_session.execute(select(Case).where(Case.id == saved_case_id))
    fetched = result.scalar_one()
    assert fetched.deleted_at is not None


async def test_delete_case_from_other_org_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_a = Organization(name="Cabinet A Delete Case")
    org_b = Organization(name="Cabinet B Delete Case")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    case_a = Case(organization_id=org_a.id, name="Dossier Protégé")
    db_session.add(case_a)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/cases/{case_a.id}",
        headers={"X-Org-Id": org_b.id},
    )
    assert response.status_code == 404


async def test_audit_log_called_on_case_mutations(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Audit Cases")
    db_session.add(org)
    await db_session.flush()

    with patch("src.routes.cases.log_action", new_callable=AsyncMock) as mock_log:
        resp = await client.post(
            "/api/v1/cases",
            json={"name": "Case Audit"},
            headers={"X-Org-Id": org.id},
        )
        assert resp.status_code == 201
        case_id = resp.json()["id"]

        await client.patch(
            f"/api/v1/cases/{case_id}",
            json={"reference": "REF-AUDIT"},
            headers={"X-Org-Id": org.id},
        )
        await client.post(
            f"/api/v1/cases/{case_id}/archive",
            headers={"X-Org-Id": org.id},
        )
        await client.delete(
            f"/api/v1/cases/{case_id}",
            headers={"X-Org-Id": org.id},
        )

        assert mock_log.call_count == 4
        actions = [call.args[0] for call in mock_log.call_args_list]
        assert actions == ["CREATE", "UPDATE", "ARCHIVE", "DELETE"]
