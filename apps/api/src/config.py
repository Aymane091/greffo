from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://greffo:greffo_local@localhost:5432/greffo_dev"
    redis_url: str = "redis://localhost:6379/0"
    environment: str = "local"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
