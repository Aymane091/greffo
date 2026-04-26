from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.db import get_db
from src.models.organization import Organization

_org_id_ctx: ContextVar[str | None] = ContextVar("org_id", default=None)
_user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        org_token = _org_id_ctx.set(request.headers.get("x-org-id"))
        user_token = _user_id_ctx.set(request.headers.get("x-user-id"))
        try:
            return await call_next(request)
        finally:
            _org_id_ctx.reset(org_token)
            _user_id_ctx.reset(user_token)


async def get_current_org(db: AsyncSession = Depends(get_db)) -> Organization:
    org_id = _org_id_ctx.get()
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Org-Id header required",
        )
    result = await db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        )
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org
