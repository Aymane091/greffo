from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def _new_ulid() -> str:
    from ulid import ULID

    return str(ULID())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_new_ulid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str | None] = mapped_column(Text, unique=True)
    siret: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    dpa_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan: Mapped[str | None] = mapped_column(Text)
    quota_minutes: Mapped[int | None] = mapped_column(Integer)
    audio_retention_days: Mapped[int] = mapped_column(Integer, server_default="30")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
