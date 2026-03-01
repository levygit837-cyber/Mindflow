"""Rate-limiting middleware — Redis-backed sliding window.

Feature-flagged via ``RATE_LIMIT_ENABLED``.  When disabled the middleware
is a transparent pass-through.

Two tiers:
- **Global:** applied to all routes.
- **Chat/Stream:** tighter limit for LLM-backed endpoints.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# Paths subject to the stricter chat/stream rate limit.
_CHAT_PATHS = {"/v1/agent/chat/stream", "/api/v1/agent/chat/stream"}


def _get_redis():
    """Lazy import of async Redis client — patchable for tests."""
    from omnimind_backend.infra.redis import get_async_redis

    return get_async_redis()


def _client_ip(request: Request) -> str:
    """Best-effort client IP extraction."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


async def _check_rate_limit(
    redis_client: object,
    key: str,
    limit: int,
    window: int,
) -> tuple[bool, int]:
    """Sliding-window rate check using Redis sorted sets.

    Returns ``(allowed, remaining)`` tuple.
    """
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
    """Redis-backed sliding-window rate limiter."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()

        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_ip = _client_ip(request)
        path = request.url.path
        window = settings.rate_limit_window_seconds

        # Determine which limit applies.
        if path in _CHAT_PATHS:
            limit = settings.rate_limit_chat_stream
            key = f"rl:chat:{client_ip}"
        else:
            limit = settings.rate_limit_global
            key = f"rl:global:{client_ip}"

        try:
            redis_client = _get_redis()
            allowed, remaining = await _check_rate_limit(redis_client, key, limit, window)
        except Exception:
            # If Redis is down, fail-open so as not to block all traffic.
            _logger.warning("rate_limiter_redis_unavailable", client_ip=client_ip)
            return await call_next(request)

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
