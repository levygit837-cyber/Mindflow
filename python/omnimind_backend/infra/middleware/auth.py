"""API Key authentication dependency.

Feature-flagged via ``AUTH_ENABLED``.  When disabled all requests pass through.
Uses ``FastAPI.Depends()`` per-route, not global middleware.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# Paths that never require authentication.
_PUBLIC_PATHS: set[str] = {"/health", "/docs", "/openapi.json", "/redoc"}


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """FastAPI dependency that validates an API key.

    Returns the API key string if valid, ``None`` when auth is disabled.

    Raises:
        HTTPException 401: Missing or invalid API key.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        return None

    # Allow public paths through.
    if request.url.path in _PUBLIC_PATHS:
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide Authorization: Bearer <key>.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials

    # Validate the key against the database.
    if not await _validate_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _logger.info("authenticated_request", api_key_prefix=api_key[:8] + "...")
    return api_key


async def _validate_key(api_key: str) -> bool:
    """Check if the API key exists in the database.

    For now, uses a simple hash-based lookup against the ``api_keys`` table.
    In the future this can be extended with expiry, scopes, etc.
    """
    import hashlib

    from sqlalchemy import select

    from omnimind_backend.storage.postgresql.connection import async_session_factory
    from omnimind_backend.storage.postgresql.models import ApiKey

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active.is_(True),
                )
            )
            return result.scalar_one_or_none() is not None
    except Exception:
        # If DB is unavailable and auth is enabled, fall back to env-based key.
        settings = get_settings()
        if settings.auth_master_key and api_key == settings.auth_master_key:
            return True
        _logger.warning("api_key_validation_db_unavailable")
        return False
