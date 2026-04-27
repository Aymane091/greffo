from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tenant import get_current_org
from src.auth.user import get_current_user_id
from src.db import get_db
from src.models.organization import Organization
from src.models.transcription import Transcription
from src.redis import get_redis
from src.schemas.transcription import (
    TranscriptionCreate,
    TranscriptionRead,
    TranscriptionUpdate,
    UploadUrlResponse,
)
from src.services import transcription_service
from src.services.audit import log_action
from src.services.storage_token import generate_upload_token
from src.utils.pagination import Page

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("", response_model=TranscriptionRead, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    payload: TranscriptionCreate,
    org: Organization = Depends(get_current_org),
    user_id: str | None = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Transcription:
    tr = await transcription_service.create_transcription(db, org.id, user_id, payload)
    await db.commit()
    await log_action("CREATE", "transcription", tr.id, org.id)
    return tr


@router.get("", response_model=Page[TranscriptionRead])
async def list_transcriptions(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    case_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Page[TranscriptionRead]:
    items, total = await transcription_service.list_transcriptions(
        db, org.id, page, size,
        case_id=case_id,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
    )
    return Page.build(items, total, page, size)  # type: ignore[return-value]


@router.get("/{tr_id}", response_model=TranscriptionRead)
async def get_transcription(
    tr_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Transcription:
    return await transcription_service.get_transcription_or_404(db, tr_id, org.id)


@router.patch("/{tr_id}", response_model=TranscriptionRead)
async def update_transcription(
    tr_id: str,
    payload: TranscriptionUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Transcription:
    tr = await transcription_service.get_transcription_or_404(db, tr_id, org.id)
    tr = await transcription_service.update_transcription(db, tr, payload)
    await db.commit()
    await log_action("UPDATE", "transcription", tr.id, org.id)
    return tr


@router.delete("/{tr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    tr_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    tr = await transcription_service.get_transcription_or_404(db, tr_id, org.id)
    tr_id_for_log = tr.id
    await transcription_service.soft_delete_transcription(db, tr)
    await db.commit()
    await log_action("DELETE", "transcription", tr_id_for_log, org.id)


@router.post("/{tr_id}/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    tr_id: str,
    request: Request,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> UploadUrlResponse:
    tr = await transcription_service.get_transcription_or_404(db, tr_id, org.id)
    if tr.audio_s3_key is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="audio_already_uploaded"
        )
    token, expires_at = generate_upload_token(tr.id, org.id)
    base_url = str(request.base_url).rstrip("/")
    upload_url = f"{base_url}/api/v1/storage/upload/{token}"
    return UploadUrlResponse(upload_url=upload_url, expires_at=expires_at)


@router.post("/{tr_id}/confirm-upload", response_model=TranscriptionRead)
async def confirm_upload(
    tr_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
    redis: object = Depends(get_redis),
) -> Transcription:
    # TODO(ticket-cleanup): job ARQ planifié toutes les heures qui supprime
    # les fichiers du storage dont aucune transcription ne référence audio_s3_key
    # (uploads où confirm-upload n'a jamais été appelé après upload réussi)
    tr = await transcription_service.get_transcription_or_404(db, tr_id, org.id)

    if tr.audio_s3_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="audio_not_uploaded"
        )

    tr.status = "queued"
    await db.commit()
    await log_action("QUEUED", "transcription", tr.id, org.id)

    await redis.enqueue_job("process_transcription", transcription_id=tr.id)  # type: ignore[union-attr]

    return tr
