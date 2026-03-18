"""Rate-limiting middleware — Redis-backed sliding window with in-memory fallback.

Feature-flagged via ``RATE_LIMIT_ENABLED`` (default: True).
When Redis is unavailable, falls back to an in-memory sliding window so rate
limiting is preserved in single-process deployments.

Three tiers:
- **Shell:** tightest limit for shell-execution endpoints (expensive, risky).
- **Chat/Stream:** tighter limit for LLM-backed endpoints.
- **Global:** applied to all other routes.

Degradation:
  Redis failures are logged as warnings.  In-memory fallback kicks in
  automatically and a counter tracks degraded periods for observability.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.security.client_ip import get_client_ip

_logger = get_logger(__name__)

# Paths subject to each rate-limit tier (checked in priority order).
_SHELL_PATHS = {
    "/v1/agent/shell-tabs",
    "/api/v1/agent/shell-tabs",
}
_CHAT_PATHS = {"/v1/agent/chat/stream", "/api/v1/agent/chat/stream"}

# ---------------------------------------------------------------------------
# In-memory fallback — per-IP timestamp lists (sliding window)
# ---------------------------------------------------------------------------
_mem_lock = asyncio.Lock()
_mem_buckets: dict[str, list[float]] = defaultdict(list)
_redis_degraded = False  # module-level flag for observability


async def _check_memory_rate_limit(
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int]:
    """Sliding-window rate check using an in-memory list.

    Returns ``(allowed, remaining)`` tuple.
    """
    now = time.monotonic()
    cutoff = now - window

    async with _mem_lock:
        bucket = _mem_buckets[key]
        # Evict expired entries
        _mem_buckets[key] = [t for t in bucket if t > cutoff]
        count = len(_mem_buckets[key])
        if count < limit:
            _mem_buckets[key].append(now)
            count += 1

    remaining = max(0, limit - count)
    return count <= limit, remaining


def _get_redis():
    """Lazy import of async Redis client — patchable for tests."""
    from mindflow_backend.infra.redis import get_async_redis

    return get_async_redis()


async def _check_redis_rate_limit(
    redis_client: object,
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int]:
    """Sliding-window rate check using Redis sorted sets."""
    now = time.time()
    window_start = now - window

    pipe = redis_client.pipeline()  # type: ignore[union-attr]
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    results = await pipe.execute()

    count = results[2]
    remaining = max(0, limit - count)
    return count <= limit, remaining


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter with Redis backend and in-memory fallback."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        global _redis_degraded

        settings = get_settings()

        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = get_client_ip(request, settings=settings)
        path = request.url.path
        window = settings.rate_limit_window_seconds

        # Determine tier
        if any(path.startswith(p) for p in _SHELL_PATHS):
            limit = getattr(settings, "rate_limit_shell", 5)  # 5/min per IP
            key = f"rl:shell:{client_ip}"
        elif path in _CHAT_PATHS:
            limit = settings.rate_limit_chat_stream
            key = f"rl:chat:{client_ip}"
        else:
            limit = settings.rate_limit_global
            key = f"rl:global:{client_ip}"

        # Try Redis first, fall back to in-memory
        allowed, remaining = True, limit
        try:
            redis_client = _get_redis()
            allowed, remaining = await _check_redis_rate_limit(redis_client, key, limit, window)
            if _redis_degraded:
                _logger.info("rate_limiter_redis_recovered")
                _redis_degraded = False
        except Exception:
            if not _redis_degraded:
                _logger.warning(
                    "rate_limiter_redis_unavailable_using_memory_fallback",
                    client_ip=client_ip,
                )
                _redis_degraded = True
            allowed, remaining = await _check_memory_rate_limit(key, limit, window)

        if not allowed:
            _logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=path,
                limit=limit,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
