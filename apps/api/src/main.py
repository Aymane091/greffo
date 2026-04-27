import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.tenant import TenantMiddleware
from src.config import settings
from src.routes import cases, health, organizations, storage, transcriptions

logger = logging.getLogger("greffo.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Storage
    from src.storage import init_storage

    app.state.storage = init_storage()

    # Redis — optional in dev_mode (graceful degradation)
    app.state.redis = None
    try:
        from urllib.parse import urlparse

        from arq import create_pool
        from arq.connections import RedisSettings

        u = urlparse(settings.redis_url)
        redis_settings = RedisSettings(
            host=u.hostname or "localhost",
            port=u.port or 6379,
            password=u.password,
            database=int(u.path.strip("/") or "0"),
        )
        app.state.redis = await create_pool(redis_settings)
    except Exception:
        if settings.dev_mode:
            logger.warning("Redis unavailable — queue disabled (dev_mode=True)")
        else:
            raise

    yield

    if app.state.redis is not None:
        await app.state.redis.aclose()


app = FastAPI(
    title="Greffo API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(transcriptions.router, prefix="/api/v1")
app.include_router(storage.router, prefix="/api/v1")
