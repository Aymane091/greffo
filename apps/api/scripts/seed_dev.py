"""
Seed script — crée une organisation de démo avec un user owner en DB.

Usage :
    uv run python scripts/seed_dev.py

Idempotent : si l'org existe déjà (même slug), le script l'affiche et s'arrête.
"""
import asyncio
import sys
from pathlib import Path

# Permet d'importer src.* sans installer le package
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.db import AsyncSessionLocal
from src.models.organization import Organization
from src.models.user import User

_ORG_NAME = "Cabinet Greffo Demo"
_ORG_SIRET = "73282932000074"
_ORG_SLUG = "cabinet-greffo-demo"
_USER_EMAIL = "demo@greffo.fr"
_USER_ROLE = "owner"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # Idempotence : vérifie si l'org existe déjà
        existing = (
            await db.execute(
                select(Organization).where(Organization.slug == _ORG_SLUG)
            )
        ).scalar_one_or_none()

        if existing is not None:
            print(f"[seed] Org déjà existante — aucune action.")
            print(f"       org_id  = {existing.id}")
            user = (
                await db.execute(
                    select(User).where(
                        User.organization_id == existing.id,
                        User.email == _USER_EMAIL,
                        User.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if user:
                print(f"       user_id = {user.id}")
            return

        org = Organization(name=_ORG_NAME, siret=_ORG_SIRET)
        db.add(org)
        await db.flush()

        import hashlib

        user = User(
            organization_id=org.id,
            email=_USER_EMAIL,
            email_hash=hashlib.sha256(_USER_EMAIL.encode()).hexdigest(),
            role=_USER_ROLE,
        )
        db.add(user)
        await db.commit()
        await db.refresh(org)
        await db.refresh(user)

    print("[seed] Données de démo créées :")
    print(f"       org_id  = {org.id}  ({org.name})")
    print(f"       user_id = {user.id}  ({user.email}, role={user.role})")
    print()
    print("Utilisation dans les requêtes curl :")
    print(f'  -H "X-Org-Id: {org.id}" -H "X-User-Id: {user.id}"')


asyncio.run(seed())
