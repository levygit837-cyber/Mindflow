"""API Key authentication dependency.

Feature-flagged via ``AUTH_ENABLED``.  When disabled all requests pass through.
Uses ``FastAPI.Depends()`` per-route, not global middleware.

Security features:
- SHA-256 key validation against DB with env-var master-key fallback
- Auth failure logging (IP, reason, timestamp)
- In-memory brute-force detection: 5 failures / 60 s → 429
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Paths that never require authentication.
_PUBLIC_PATHS: set[str] = {"/health", "/docs", "/openapi.json", "/redoc"}

# ---------------------------------------------------------------------------
# Brute-force detection — in-memory sliding window (no Redis dependency)
# Structure: { ip: [(timestamp, ...), ...] }
# ---------------------------------------------------------------------------
_BRUTE_WINDOW_SECONDS = 60
_BRUTE_MAX_FAILURES = 5

# asyncio.Lock is not shared-state safe across workers, but is fine for
# single-process deployments. For multi-process, migrate to Redis.
_failure_lock = asyncio.Lock()
_failures: dict[str, list[float]] = defaultdict(list)


async def _record_failure(client_ip: str) -> bool:
    """Record an auth failure and return True if the IP should be blocked."""
    now = time.monotonic()
    cutoff = now - _BRUTE_WINDOW_SECONDS

    async with _failure_lock:
        # Evict old entries
        _failures[client_ip] = [t for t in _failures[client_ip] if t > cutoff]
        _failures[client_ip].append(now)
        count = len(_failures[client_ip])

    if count >= _BRUTE_MAX_FAILURES:
        _logger.warning(
            "auth_brute_force_detected",
            client_ip=client_ip,
            failure_count=count,
            window_seconds=_BRUTE_WINDOW_SECONDS,
        )
        return True
    return False


async def _is_ip_blocked(client_ip: str) -> bool:
    """Return True if the IP has exceeded the failure threshold."""
    now = time.monotonic()
    cutoff = now - _BRUTE_WINDOW_SECONDS
    async with _failure_lock:
        recent = [t for t in _failures[client_ip] if t > cutoff]
    return len(recent) >= _BRUTE_MAX_FAILURES


# ---------------------------------------------------------------------------
# Public dependency
# ---------------------------------------------------------------------------


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """FastAPI dependency that validates an API key.

    Returns the API key string if valid, ``None`` when auth is disabled.

    Raises:
        HTTPException 429: IP blocked due to repeated failures.
        HTTPException 401: Missing or invalid API key.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        return None

    # Allow public paths through.
    if request.url.path in _PUBLIC_PATHS:
        return None

    client_ip = request.client.host if request.client else "unknown"

    # Check brute-force block before processing credentials
    if await _is_ip_blocked(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Try again later.",
            headers={"Retry-After": str(_BRUTE_WINDOW_SECONDS)},
        )

    if credentials is None:
        await _record_failure(client_ip)
        _logger.warning(
            "auth_failure",
            reason="missing_credentials",
            client_ip=client_ip,
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide Authorization: Bearer <key>.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials

    # Validate the key against the database.
    if not await _validate_key(api_key):
        blocked = await _record_failure(client_ip)
        _logger.warning(
            "auth_failure",
            reason="invalid_key",
            client_ip=client_ip,
            path=request.url.path,
            # Log only a short prefix to aid correlation without exposing the key
            key_prefix=api_key[:4] + "****" if len(api_key) > 4 else "****",
        )
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed authentication attempts. Try again later.",
                headers={"Retry-After": str(_BRUTE_WINDOW_SECONDS)},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _logger.info(
        "auth_success",
        client_ip=client_ip,
        path=request.url.path,
    )
    return api_key


# ---------------------------------------------------------------------------
# Key validation
# ---------------------------------------------------------------------------


async def _validate_key(api_key: str) -> bool:
    """Check if the API key exists in the database.

    Falls back to ``AUTH_MASTER_KEY`` env var when the DB is unavailable.
    """
    from sqlalchemy import select

    from mindflow_backend.storage import ApiKey, async_session_factory

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active.is_(True),
                )
            )
            if result.scalar_one_or_none() is not None:
                return True
    except Exception:
        pass  # Fall through to master-key check below

    # Master key fallback (also covers DB-unavailable path)
    settings = get_settings()
    master_key = getattr(settings, "auth_master_key", None)
    if master_key and api_key == master_key:
        return True

    _logger.warning("api_key_validation_db_unavailable_or_no_match")
    return False
