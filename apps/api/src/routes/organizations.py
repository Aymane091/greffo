from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tenant import get_current_org
from src.db import get_db
from src.models.organization import Organization
from src.models.user import User
from src.schemas.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    UserRead,
)
from src.services.audit import log_action

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
) -> Organization:
    org = Organization(
        name=payload.name,
        slug=payload.effective_slug(),
        siret=payload.siret,
    )
    db.add(org)
    await db.flush()
    await db.commit()
    await log_action("CREATE", "organization", org.id, org.id)
    return org


@router.get("/me", response_model=OrganizationRead)
async def get_my_organization(
    org: Organization = Depends(get_current_org),
) -> Organization:
    return org


@router.patch("/me", response_model=OrganizationRead)
async def update_my_organization(
    payload: OrganizationUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    if payload.name is not None:
        org.name = payload.name
    if payload.address is not None:
        org.address = payload.address
    await db.flush()
    await db.commit()
    await log_action("UPDATE", "organization", org.id, org.id)
    return org


@router.get("/me/users", response_model=list[UserRead])
async def list_organization_users(
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.organization_id == org.id, User.deleted_at.is_(None))
        .order_by(User.created_at)
    )
    return list(result.scalars().all())
