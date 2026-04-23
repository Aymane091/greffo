from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def _new_ulid() -> str:
    from ulid import ULID

    return str(ULID())


class Transcription(Base):
    __tablename__ = "transcriptions"
    __table_args__ = (
        Index("ix_transcriptions_org_created_at", "organization_id", "created_at"),
        Index("ix_transcriptions_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_new_ulid)
    organization_id: Mapped[str] = mapped_column(
        Text, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str | None] = mapped_column(Text, ForeignKey("cases.id"))
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)

    audio_s3_key: Mapped[str | None] = mapped_column(Text)
    audio_duration_s: Mapped[int | None] = mapped_column(Integer)
    audio_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    audio_format: Mapped[str | None] = mapped_column(Text)
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    progress_pct: Mapped[int | None] = mapped_column(SmallInteger)

    language: Mapped[str] = mapped_column(Text, nullable=False, server_default="fr")
    speaker_count: Mapped[int | None] = mapped_column(SmallInteger)

    transcript_s3_key: Mapped[str | None] = mapped_column(Text)
    transcript_preview: Mapped[str | None] = mapped_column(Text)

    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cost_minutes_used: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
