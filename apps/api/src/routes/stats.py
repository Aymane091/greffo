from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tenant import get_current_org
from src.db import get_db
from src.models.case import Case
from src.models.organization import Organization
from src.models.transcription import Transcription

router = APIRouter(prefix="/stats", tags=["stats"])


class DashboardStats(BaseModel):
    active_cases: int
    archived_cases: int
    transcriptions_this_month: int
    total_audio_duration_seconds: float
    status_breakdown: dict[str, int]


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Active + archived cases (single query with FILTER)
    cases_row = (
        await db.execute(
            select(
                func.count().filter(Case.archived_at.is_(None)).label("active"),
                func.count().filter(Case.archived_at.isnot(None)).label("archived"),
            ).where(Case.organization_id == org.id)
        )
    ).one()

    # 2. Transcriptions this month
    tr_count_row = (
        await db.execute(
            select(func.count()).where(
                Transcription.organization_id == org.id,
                Transcription.created_at >= month_start,
            )
        )
    ).scalar_one()

    # 3. Total audio duration this month (done only)
    duration_row = (
        await db.execute(
            select(func.coalesce(func.sum(Transcription.audio_duration_s), 0)).where(
                Transcription.organization_id == org.id,
                Transcription.status == "done",
                Transcription.created_at >= month_start,
            )
        )
    ).scalar_one()

    # 4. Status breakdown this month
    status_rows = (
        await db.execute(
            select(Transcription.status, func.count().label("cnt"))
            .where(
                Transcription.organization_id == org.id,
                Transcription.created_at >= month_start,
            )
            .group_by(Transcription.status)
        )
    ).all()

    breakdown: dict[str, int] = {"done": 0, "processing": 0, "failed": 0, "queued": 0}
    for row in status_rows:
        if row.status in breakdown:
            breakdown[row.status] = row.cnt

    return DashboardStats(
        active_cases=cases_row.active,
        archived_cases=cases_row.archived,
        transcriptions_this_month=tr_count_row,
        total_audio_duration_seconds=float(duration_row),
        status_breakdown=breakdown,
    )
