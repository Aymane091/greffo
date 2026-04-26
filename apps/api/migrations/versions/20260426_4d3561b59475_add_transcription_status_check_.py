"""add_transcription_status_check_constraint

Revision ID: 4d3561b59475
Revises: c080bc1d768e
Create Date: 2026-04-26 18:02:49.725757+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4d3561b59475'
down_revision: Union[str, None] = 'c080bc1d768e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_VALID_STATUSES = (
    "'draft', 'queued', 'processing', 'transcribing', 'diarizing', 'aligning', 'done', 'failed'"
)


def upgrade() -> None:
    op.create_check_constraint(
        "transcriptions_status_check",
        "transcriptions",
        f"status IN ({_VALID_STATUSES})",
    )


def downgrade() -> None:
    op.drop_constraint("transcriptions_status_check", "transcriptions", type_="check")
