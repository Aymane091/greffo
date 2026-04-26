# TODO: À l'avenir, créer automatiquement un case "Non classé" par défaut à
# l'inscription d'une org pour permettre des uploads rapides sans choix manuel.
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.models.transcription import Transcription
from src.schemas.transcription import TranscriptionCreate, TranscriptionUpdate


async def create_transcription(
    db: AsyncSession,
    org_id: str,
    user_id: str | None,
    payload: TranscriptionCreate,
) -> Transcription:
    # Vérifie que le case appartient bien à l'org (isolation tenant)
    case_result = await db.execute(
        select(Case).where(
            Case.id == payload.case_id,
            Case.organization_id == org_id,
            Case.deleted_at.is_(None),
        )
    )
    if case_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    tr = Transcription(
        organization_id=org_id,
        case_id=payload.case_id,
        user_id=user_id,
        title=payload.title,
        language=payload.language,
        status="draft",
    )
    db.add(tr)
    await db.flush()
    return tr


async def get_transcription_or_404(
    db: AsyncSession, tr_id: str, org_id: str
) -> Transcription:
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == tr_id,
            Transcription.organization_id == org_id,
            Transcription.deleted_at.is_(None),
        )
    )
    tr = result.scalar_one_or_none()
    if tr is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transcription not found"
        )
    return tr


async def list_transcriptions(
    db: AsyncSession,
    org_id: str,
    page: int,
    size: int,
    case_id: str | None,
    status_filter: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[list[Transcription], int]:
    base_q = select(Transcription).where(
        Transcription.organization_id == org_id,
        Transcription.deleted_at.is_(None),
    )
    if case_id is not None:
        base_q = base_q.where(Transcription.case_id == case_id)
    if status_filter is not None:
        base_q = base_q.where(Transcription.status == status_filter)
    if from_date is not None:
        base_q = base_q.where(Transcription.created_at >= from_date)
    if to_date is not None:
        base_q = base_q.where(Transcription.created_at <= to_date)

    total: int = (
        await db.execute(select(func.count()).select_from(base_q.subquery()))
    ).scalar_one()
    items = list(
        (
            await db.execute(
                base_q.order_by(Transcription.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        .scalars()
        .all()
    )
    return items, total


async def update_transcription(
    db: AsyncSession, tr: Transcription, payload: TranscriptionUpdate
) -> Transcription:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tr, field, value)
    await db.flush()
    return tr


async def soft_delete_transcription(db: AsyncSession, tr: Transcription) -> None:
    tr.deleted_at = datetime.now(timezone.utc)
    await db.flush()
