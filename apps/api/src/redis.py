import logging

from src.config import settings

logger = logging.getLogger("greffo.redis")


class _NoOpRedis:
    """Used in dev_mode when Redis is unavailable. Logs enqueue calls instead of sending them."""

    async def enqueue_job(self, fn_name: str, **kwargs: object) -> None:
        logger.warning("No-op enqueue_job: %s %s (Redis unavailable)", fn_name, kwargs)


def get_redis() -> object:
    """FastAPI dependency — returns ArqRedis in prod, _NoOpRedis in dev, FakeRedis in tests."""
    from src.main import app

    redis = getattr(app.state, "redis", None)
    if redis is None:
        if settings.dev_mode:
            return _NoOpRedis()
        raise RuntimeError("Redis pool not initialized")
    return redis
