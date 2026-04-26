from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ArchivedFilter(str, Enum):
    false = "false"
    true = "true"
    all = "all"


class CaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    reference: str | None = None
    description: str | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    reference: str | None
    description: str | None
    created_by: str | None
    archived_at: datetime | None
    created_at: datetime


class CaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    reference: str | None = None
    description: str | None = None
