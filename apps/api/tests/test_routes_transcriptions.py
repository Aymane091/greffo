from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.models.user import User
from tests.conftest import FakeRedis


def _h(org_id: str, user_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"X-Org-Id": org_id}
    if user_id is not None:
        headers["X-User-Id"] = user_id
    return headers


async def test_create_transcription_returns_201_with_draft_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr Création")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="tr1@cabinet.fr", email_hash="htr1", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier Tr1")
    db_session.add_all([user, case])
    await db_session.flush()

    response = await client.post(
        "/api/v1/transcriptions",
        json={"case_id": case.id, "title": "Audition 01"},
        headers=_h(org.id, user.id),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["title"] == "Audition 01"
    assert data["language"] == "fr"
    assert len(data["id"]) == 26


async def test_create_transcription_missing_title_returns_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr 422")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="tr422@cabinet.fr", email_hash="htr422", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier 422")
    db_session.add_all([user, case])
    await db_session.flush()

    response = await client.post(
        "/api/v1/transcriptions",
        json={"case_id": case.id},
        headers=_h(org.id, user.id),
    )
    assert response.status_code == 422


async def test_list_transcriptions_pagination(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr Pagination")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="trpag@cabinet.fr", email_hash="htrpag", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier Pag")
    db_session.add_all([user, case])
    await db_session.flush()

    for i in range(3):
        db_session.add(
            Transcription(
                organization_id=org.id,
                user_id=user.id,
                case_id=case.id,
                title=f"Audition {i}",
                status="draft",
                language="fr",
            )
        )
    await db_session.flush()

    response = await client.get(
        "/api/v1/transcriptions?page=1&size=2",
        headers=_h(org.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


async def test_list_transcriptions_filter_by_case_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr Filtre")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="trfilt@cabinet.fr", email_hash="htrfilt", role="member"
    )
    case_a = Case(organization_id=org.id, name="Dossier A")
    case_b = Case(organization_id=org.id, name="Dossier B")
    db_session.add_all([user, case_a, case_b])
    await db_session.flush()

    for i in range(2):
        db_session.add(
            Transcription(
                organization_id=org.id,
                user_id=user.id,
                case_id=case_a.id,
                title=f"Tr A{i}",
                status="draft",
                language="fr",
            )
        )
    db_session.add(
        Transcription(
            organization_id=org.id,
            user_id=user.id,
            case_id=case_b.id,
            title="Tr B0",
            status="draft",
            language="fr",
        )
    )
    await db_session.flush()

    response = await client.get(
        f"/api/v1/transcriptions?case_id={case_a.id}",
        headers=_h(org.id),
    )
    data = response.json()
    assert data["total"] == 2
    assert all(item["case_id"] == case_a.id for item in data["items"])


async def test_get_transcription_detail(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr Détail")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="trd@cabinet.fr", email_hash="htrd", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier Détail")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="Audition Détail",
        status="draft",
        language="fr",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/transcriptions/{tr.id}",
        headers=_h(org.id),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Audition Détail"


async def test_get_transcription_from_other_org_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_a = Organization(name="Cabinet Tr Iso A")
    org_b = Organization(name="Cabinet Tr Iso B")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    user_a = User(
        organization_id=org_a.id,
        email="trisa@cabinet.fr",
        email_hash="htrisa",
        role="member",
    )
    case_a = Case(organization_id=org_a.id, name="Dossier Iso A")
    db_session.add_all([user_a, case_a])
    await db_session.flush()
    tr_a = Transcription(
        organization_id=org_a.id,
        user_id=user_a.id,
        case_id=case_a.id,
        title="Tr Confidentielle",
        status="draft",
        language="fr",
    )
    db_session.add(tr_a)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/transcriptions/{tr_a.id}",
        headers=_h(org_b.id),
    )
    assert response.status_code == 404


async def test_patch_transcription_title_and_case(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Tr Patch")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="trpatch@cabinet.fr", email_hash="htrpatch", role="member"
    )
    case_a = Case(organization_id=org.id, name="Dossier Patch A")
    case_b = Case(organization_id=org.id, name="Dossier Patch B")
    db_session.add_all([user, case_a, case_b])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case_a.id,
        title="Ancien Titre",
        status="draft",
        language="fr",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/transcriptions/{tr.id}",
        json={"title": "Nouveau Titre", "case_id": case_b.id},
        headers=_h(org.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Nouveau Titre"
    assert data["case_id"] == case_b.id


async def test_soft_delete_transcription(
    client: AsyncClient, db_session: AsyncSession, tmp_storage
) -> None:
    org = Organization(name="Cabinet Tr Delete")
    db_session.add(org)
    await db_session.flush()
    user = User(
        organization_id=org.id, email="trdel@cabinet.fr", email_hash="htrdel", role="member"
    )
    case = Case(organization_id=org.id, name="Dossier Delete")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id,
        user_id=user.id,
        case_id=case.id,
        title="À Supprimer",
        status="draft",
        language="fr",
    )
    db_session.add(tr)
    await db_session.flush()

    saved_tr_id = tr.id  # sauvegarder avant expire_all
    response = await client.delete(
        f"/api/v1/transcriptions/{saved_tr_id}",
        headers=_h(org.id),
    )
    assert response.status_code == 204

    list_resp = await client.get("/api/v1/transcriptions", headers=_h(org.id))
    ids = [t["id"] for t in list_resp.json()["items"]]
    assert saved_tr_id not in ids

    db_session.expire_all()
    result = await db_session.execute(
        select(Transcription).where(Transcription.id == saved_tr_id)
    )
    fetched = result.scalar_one()
    assert fetched.deleted_at is not None


async def test_user_from_other_org_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_a = Organization(name="Cabinet Auth Tr A")
    org_b = Organization(name="Cabinet Auth Tr B")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    user_b = User(
        organization_id=org_b.id,
        email="userb_trauth@cabinet.fr",
        email_hash="huserb_trauth",
        role="member",
    )
    case_a = Case(organization_id=org_a.id, name="Dossier Auth A")
    db_session.add_all([user_b, case_a])
    await db_session.flush()

    # X-Org-Id = org_a, X-User-Id = user_b (appartient à org_b) → 401
    response = await client.post(
        "/api/v1/transcriptions",
        json={"case_id": case_a.id, "title": "Tentative Intrusion"},
        headers={"X-Org-Id": org_a.id, "X-User-Id": user_b.id},
    )
    assert response.status_code == 401


# ── Audio stream ──────────────────────────────────────────────────────────────

async def test_stream_audio_returns_200_with_content_type(
    client: AsyncClient, db_session: AsyncSession, tmp_storage
) -> None:
    org = Organization(name="Cabinet Audio OK")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="audioOK@cabinet.fr", email_hash="haudioOK", role="member")
    case = Case(organization_id=org.id, name="Dossier Audio OK")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id, user_id=user.id, case_id=case.id,
        title="Audio Test", status="done", language="fr",
        audio_s3_key="audio/tr-audio-ok", audio_format="mp3",
    )
    db_session.add(tr)
    await db_session.flush()
    await tmp_storage.upload("audio/tr-audio-ok", b"ID3fake-mp3-bytes", "audio/mpeg")

    response = await client.get(f"/api/v1/transcriptions/{tr.id}/audio", headers=_h(org.id))
    assert response.status_code == 200
    assert "audio" in response.headers["content-type"]


async def test_stream_audio_404_when_no_audio_key(
    client: AsyncClient, db_session: AsyncSession, tmp_storage
) -> None:
    org = Organization(name="Cabinet Audio NoKey")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="audioNK@cabinet.fr", email_hash="haudioNK", role="member")
    case = Case(organization_id=org.id, name="Dossier Audio NK")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id, user_id=user.id, case_id=case.id,
        title="No Audio", status="draft", language="fr",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.get(f"/api/v1/transcriptions/{tr.id}/audio", headers=_h(org.id))
    assert response.status_code == 404
    assert response.json()["detail"] == "audio_not_found"


async def test_stream_audio_404_for_other_org(
    client: AsyncClient, db_session: AsyncSession, tmp_storage
) -> None:
    org_a = Organization(name="Cabinet Audio Org A")
    org_b = Organization(name="Cabinet Audio Org B")
    db_session.add_all([org_a, org_b])
    await db_session.flush()
    user_a = User(organization_id=org_a.id, email="audioA@cabinet.fr", email_hash="haudioA", role="member")
    case_a = Case(organization_id=org_a.id, name="Dossier Audio A")
    db_session.add_all([user_a, case_a])
    await db_session.flush()
    tr = Transcription(
        organization_id=org_a.id, user_id=user_a.id, case_id=case_a.id,
        title="Audio Org A", status="done", language="fr",
        audio_s3_key="audio/org-a-audio", audio_format="mp3",
    )
    db_session.add(tr)
    await db_session.flush()
    await tmp_storage.upload("audio/org-a-audio", b"bytes", "audio/mpeg")

    response = await client.get(f"/api/v1/transcriptions/{tr.id}/audio", headers=_h(org_b.id))
    assert response.status_code == 404


# ── Retry ─────────────────────────────────────────────────────────────────────

async def test_retry_transcription_from_failed(
    client: AsyncClient, db_session: AsyncSession, fake_redis: FakeRedis
) -> None:
    org = Organization(name="Cabinet Retry")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="retry@cabinet.fr", email_hash="hretry", role="member")
    case = Case(organization_id=org.id, name="Dossier Retry")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id, user_id=user.id, case_id=case.id,
        title="Failed Tr", status="failed", language="fr",
        error_code="network_error", error_message="Connection refused",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.post(f"/api/v1/transcriptions/{tr.id}/retry", headers=_h(org.id))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert data["error_code"] is None
    assert data["error_message"] is None
    assert any(j["fn"] == "process_transcription" and j["transcription_id"] == tr.id for j in fake_redis.enqueued)


async def test_retry_non_failed_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org = Organization(name="Cabinet Retry 409")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="retry409@cabinet.fr", email_hash="hretry409", role="member")
    case = Case(organization_id=org.id, name="Dossier Retry 409")
    db_session.add_all([user, case])
    await db_session.flush()
    tr = Transcription(
        organization_id=org.id, user_id=user.id, case_id=case.id,
        title="Done Tr", status="done", language="fr",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.post(f"/api/v1/transcriptions/{tr.id}/retry", headers=_h(org.id))
    assert response.status_code == 409
    assert "can_only_retry_failed" in response.json()["detail"]


# ── Delete + storage cleanup ──────────────────────────────────────────────────

async def test_delete_transcription_removes_audio_file(
    client: AsyncClient, db_session: AsyncSession, tmp_storage
) -> None:
    org = Organization(name="Cabinet Del Audio")
    db_session.add(org)
    await db_session.flush()
    user = User(organization_id=org.id, email="delaudio@cabinet.fr", email_hash="hdelaudio", role="member")
    case = Case(organization_id=org.id, name="Dossier Del Audio")
    db_session.add_all([user, case])
    await db_session.flush()

    audio_key = "audio/del-test-id"
    await tmp_storage.upload(audio_key, b"audio-bytes", "audio/mpeg")
    assert await tmp_storage.exists(audio_key)

    tr = Transcription(
        organization_id=org.id, user_id=user.id, case_id=case.id,
        title="À Supprimer Avec Audio", status="done", language="fr",
        audio_s3_key=audio_key, audio_format="mp3",
    )
    db_session.add(tr)
    await db_session.flush()

    response = await client.delete(f"/api/v1/transcriptions/{tr.id}", headers=_h(org.id))
    assert response.status_code == 204
    assert not await tmp_storage.exists(audio_key)
