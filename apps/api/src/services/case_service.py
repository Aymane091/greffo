from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.case import Case
from src.schemas.case import ArchivedFilter, CaseCreate, CaseUpdate


async def create_case(db: AsyncSession, org_id: str, payload: CaseCreate) -> Case:
    case = Case(
        organization_id=org_id,
        name=payload.name,
        reference=payload.reference,
        description=payload.description,
    )
    db.add(case)
    await db.flush()
    return case


async def get_case_or_404(db: AsyncSession, case_id: str, org_id: str) -> Case:
    result = await db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.organization_id == org_id,
            Case.deleted_at.is_(None),
        )
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


async def list_cases(
    db: AsyncSession,
    org_id: str,
    page: int,
    size: int,
    archived: ArchivedFilter,
) -> tuple[list[Case], int]:
    base_q = select(Case).where(
        Case.organization_id == org_id,
        Case.deleted_at.is_(None),
    )
    if archived == ArchivedFilter.false:
        base_q = base_q.where(Case.archived_at.is_(None))
    elif archived == ArchivedFilter.true:
        base_q = base_q.where(Case.archived_at.isnot(None))
    # ArchivedFilter.all : pas de filtre supplémentaire

    total: int = (
        await db.execute(select(func.count()).select_from(base_q.subquery()))
    ).scalar_one()
    items = list(
        (
            await db.execute(
                base_q.order_by(Case.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        .scalars()
        .all()
    )
    return items, total


async def update_case(db: AsyncSession, case: Case, payload: CaseUpdate) -> Case:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(case, field, value)
    await db.flush()
    return case


async def archive_case(db: AsyncSession, case: Case) -> Case:
    case.archived_at = datetime.now(timezone.utc)
    await db.flush()
    return case


async def soft_delete_case(db: AsyncSession, case: Case) -> None:
    case.deleted_at = datetime.now(timezone.utc)
    await db.flush()
