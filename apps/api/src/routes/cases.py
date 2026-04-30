from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tenant import get_current_org
from src.db import get_db
from src.models.case import Case
from src.models.organization import Organization
from src.schemas.case import ArchivedFilter, CaseCreate, CaseRead, CaseUpdate
from src.schemas.transcription import TranscriptionRead
from src.services import case_service, transcription_service
from src.services.audit import log_action
from src.utils.pagination import Page

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
async def create_case(
    payload: CaseCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await case_service.create_case(db, org.id, payload)
    await db.commit()
    await log_action("CREATE", "case", case.id, org.id)
    return case


@router.get("", response_model=Page[CaseRead])
async def list_cases(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    archived: ArchivedFilter = Query(ArchivedFilter.false),
    query: str | None = Query(None, max_length=200),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Page[CaseRead]:
    items, total = await case_service.list_cases(db, org.id, page, size, archived, query)
    return Page.build(items, total, page, size)  # type: ignore[return-value]


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Case:
    return await case_service.get_case_or_404(db, case_id, org.id)


@router.patch("/{case_id}", response_model=CaseRead)
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await case_service.get_case_or_404(db, case_id, org.id)
    case = await case_service.update_case(db, case, payload)
    await db.commit()
    await log_action("UPDATE", "case", case.id, org.id)
    return case


@router.post("/{case_id}/archive", response_model=CaseRead)
async def archive_case(
    case_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await case_service.get_case_or_404(db, case_id, org.id)
    case = await case_service.archive_case(db, case)
    await db.commit()
    await log_action("ARCHIVE", "case", case.id, org.id)
    return case


@router.post("/{case_id}/unarchive", response_model=CaseRead)
async def unarchive_case(
    case_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Case:
    case = await case_service.get_case_or_404(db, case_id, org.id)
    case = await case_service.unarchive_case(db, case)
    await db.commit()
    await log_action("UNARCHIVE", "case", case.id, org.id)
    return case


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    case = await case_service.get_case_or_404(db, case_id, org.id)
    case_id_for_log = case.id
    await case_service.soft_delete_case(db, case)
    await db.commit()
    await log_action("DELETE", "case", case_id_for_log, org.id)


@router.get("/{case_id}/transcriptions", response_model=Page[TranscriptionRead])
async def list_case_transcriptions(
    case_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Page[TranscriptionRead]:
    await case_service.get_case_or_404(db, case_id, org.id)
    items, total = await transcription_service.list_transcriptions(
        db, org.id, page, size,
        case_id=case_id, status_filter=None, from_date=None, to_date=None,
    )
    return Page.build(items, total, page, size)  # type: ignore[return-value]
