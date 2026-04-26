import re
import unicodedata
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower())
    return slug.strip("-")


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = None
    siret: str | None = None

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"\d{14}", v):
            raise ValueError("SIRET must be exactly 14 digits")
        return v

    def effective_slug(self) -> str:
        return self.slug or _slugify(self.name)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str | None
    siret: str | None
    address: str | None
    plan: str | None
    quota_minutes: int | None
    audio_retention_days: int
    created_at: datetime
    updated_at: datetime | None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    address: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    role: str
    created_at: datetime
