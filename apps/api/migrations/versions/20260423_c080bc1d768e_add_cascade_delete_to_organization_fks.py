"""add_cascade_delete_to_organization_fks

Revision ID: c080bc1d768e
Revises: fe8d33c28e88
Create Date: 2026-04-23 16:24:42.259177+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c080bc1d768e'
down_revision: Union[str, None] = 'fe8d33c28e88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_organization_id_fkey", "users", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("cases_organization_id_fkey", "cases", type_="foreignkey")
    op.create_foreign_key(
        "cases_organization_id_fkey", "cases", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )

    op.drop_constraint("transcriptions_organization_id_fkey", "transcriptions", type_="foreignkey")
    op.create_foreign_key(
        "transcriptions_organization_id_fkey", "transcriptions", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("transcriptions_organization_id_fkey", "transcriptions", type_="foreignkey")
    op.create_foreign_key(
        "transcriptions_organization_id_fkey", "transcriptions", "organizations",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("cases_organization_id_fkey", "cases", type_="foreignkey")
    op.create_foreign_key(
        "cases_organization_id_fkey", "cases", "organizations",
        ["organization_id"], ["id"],
    )

    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_organization_id_fkey", "users", "organizations",
        ["organization_id"], ["id"],
    )
