from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TranscriptionCreate(BaseModel):
    case_id: str
    title: str = Field(min_length=2, max_length=200)
    language: str = "fr"
    # user_id est injecté via Depends(get_current_user_id) — jamais dans le body


class TranscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    case_id: str | None
    user_id: str | None
    title: str | None
    status: str
    progress_pct: int | None
    language: str
    audio_duration_s: int | None
    audio_size_bytes: int | None
    audio_format: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    processing_started_at: datetime | None
    processing_ended_at: datetime | None


class TranscriptionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    case_id: str | None = None


class UploadUrlResponse(BaseModel):
    upload_url: str
    expires_at: datetime
