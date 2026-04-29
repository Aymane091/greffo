"""add_auth_verification_tokens_table

Revision ID: 54ea5955c166
Revises: 752a4e2476c1
Create Date: 2026-04-29 13:58:54.062411+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '54ea5955c166'
down_revision: Union[str, None] = '752a4e2476c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_verification_tokens',
        sa.Column('identifier', sa.Text(), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('expires', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('identifier', 'token'),
    )


def downgrade() -> None:
    op.drop_table('auth_verification_tokens')
