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

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://greffo@localhost:5432/greffo_test",
)
_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
_API_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="session", autouse=True)
async def apply_migrations() -> AsyncGenerator[None, None]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m", "alembic", "upgrade", "head",
        cwd=_API_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    assert proc.returncode == 0, f"Alembic migration failed:\n{stderr.decode()}"
    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield session

        app.dependency_overrides[get_db] = override_get_db
        yield session
        await session.close()
        await conn.rollback()
        app.dependency_overrides.clear()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
