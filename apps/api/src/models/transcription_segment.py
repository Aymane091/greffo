from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def _new_ulid() -> str:
    from ulid import ULID

    return str(ULID())


class TranscriptionSegment(Base):
    __tablename__ = "transcription_segments"
    __table_args__ = (
        Index("ix_segments_transcription_id", "transcription_id"),
        Index("ix_segments_org_id", "organization_id"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=_new_ulid)
    transcription_id: Mapped[str] = mapped_column(
        Text, ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        Text, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(Text)
    start_s: Mapped[float] = mapped_column(Double, nullable=False)
    end_s: Mapped[float] = mapped_column(Double, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
