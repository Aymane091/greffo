import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.db import get_db
from src.main import app
from src.redis import get_redis
from src.storage import get_storage

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://greffo@localhost:5432/greffo_test",
)
_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
_API_DIR = Path(__file__).parent.parent


class FakeRedis:
    def __init__(self) -> None:
        self.enqueued: list[dict] = []

    async def enqueue_job(self, fn_name: str, **kwargs: object) -> None:
        self.enqueued.append({"fn": fn_name, **kwargs})


@pytest.fixture(scope="session", autouse=True)
async def apply_migrations() -> AsyncGenerator[None, None]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=_API_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, f"Alembic migration failed:\n{stderr.decode()}"
    yield


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture
async def db_session(fake_redis: FakeRedis) -> AsyncGenerator[AsyncSession, None]:
    async with _test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield session

        # Snapshot pre-existing overrides so other fixtures' overrides survive our reset
        _saved_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_redis] = lambda: fake_redis

        yield session

        await session.close()
        await conn.rollback()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(_saved_overrides)


@pytest.fixture
async def tmp_storage(db_session: AsyncSession, tmp_path: Path) -> AsyncGenerator:
    """Local storage backend isolated to tmp_path, wired into FastAPI dependency."""
    from src.storage.local import LocalStorageBackend

    backend = LocalStorageBackend(tmp_path / "audio")
    app.dependency_overrides[get_storage] = lambda: backend
    yield backend
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
