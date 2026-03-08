from functools import lru_cache

try:
    import redis  # type: ignore
    import redis.asyncio as redis_async  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    redis = None  # type: ignore[assignment]
    redis_async = None  # type: ignore[assignment]

from .config import get_settings


@lru_cache(maxsize=1)
def get_sync_redis():
    settings = get_settings()
    if redis is None:  # pragma: no cover
        raise RuntimeError(
            "redis package is not installed. Install it to use Redis-backed features."
        )
    return redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache(maxsize=1)
def get_async_redis():
    settings = get_settings()
    if redis_async is None:  # pragma: no cover
        raise RuntimeError(
            "redis package is not installed. Install it to use Redis-backed features."
        )
    return redis_async.from_url(settings.redis_url, decode_responses=True)
