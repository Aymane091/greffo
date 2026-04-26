import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tenant import _user_id_ctx, get_current_org
from src.config import settings
from src.db import get_db
from src.models.organization import Organization
from src.models.user import User

logger = logging.getLogger(__name__)


async def get_current_user_id(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> str | None:
    user_id = _user_id_ctx.get()

    if user_id is None:
        if settings.dev_mode:
            logger.warning("X-User-Id header manquant (dev mode) — user_id sera None")
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-User-Id header required",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == org.id,
            User.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User does not belong to this organization",
        )

    return user_id
