from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://greffo:greffo_local@localhost:5432/greffo_dev"
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "local"
    debug: bool = False
    dev_mode: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]

    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    storage_secret: str = "change-me-in-production-use-32-chars-min"

    # Transcription provider
    transcription_provider: Literal["stub", "gladia"] = "stub"
    gladia_api_key: str | None = None
    gladia_base_url: str = "https://api.gladia.io"
    transcription_timeout_seconds: int = 1800

    @model_validator(mode="after")
    def _require_gladia_key(self) -> "Settings":
        if self.transcription_provider == "gladia" and not (self.gladia_api_key or "").strip():
            raise ValueError(
                "GLADIA_API_KEY must be set (non-empty) when TRANSCRIPTION_PROVIDER=gladia"
            )
        return self


settings = Settings()
