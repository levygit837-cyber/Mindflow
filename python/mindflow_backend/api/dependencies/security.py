"""Security dependencies shared across routers."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from mindflow_backend.infra.middleware.auth import require_api_key
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Base auth dependency — all authenticated routes use this
# ---------------------------------------------------------------------------
protected_route_dependencies = [Depends(require_api_key)]

# ---------------------------------------------------------------------------
# API-key "role" resolution
#
# Until a full user/role DB is in place we use a simple convention:
#   - AUTH_MASTER_KEY → role "admin"
#   - Any other valid key → role "user"
# ---------------------------------------------------------------------------


async def _get_caller_role(
    request: Request,
    api_key: str | None = Depends(require_api_key),
) -> str:
    """Return the caller's role string based on the validated API key."""
    if api_key is None:
        # Auth is disabled — grant admin to allow local dev to work normally.
        return "admin"

    from mindflow_backend.infra.config import get_settings

    settings = get_settings()
    master_key = settings.auth_master_key if hasattr(settings, "auth_master_key") else None
    if master_key and api_key == master_key:
        return "admin"
    return "user"


async def require_admin(
    role: str = Depends(_get_caller_role),
) -> str:
    """FastAPI dependency that enforces 'admin' role.

    Raises 403 if the caller is authenticated but not an admin.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )
    return role


# ---------------------------------------------------------------------------
# Audit logging decorator
# ---------------------------------------------------------------------------


def audit_log(action: str, resource: str):
    """Decorator that logs an audit event around a route handler.

    Usage::

        @router.put("/config/")
        @audit_log(action="update", resource="config")
        async def update_config(...):
            ...
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs (FastAPI injects it by name)
            request: Request | None = kwargs.get("request")
            caller_ip = request.client.host if request and request.client else "unknown"

            try:
                result = await func(*args, **kwargs)
                _logger.info(
                    "audit_event",
                    action=action,
                    resource=resource,
                    caller_ip=caller_ip,
                    result="success",
                )
                return result
            except HTTPException as exc:
                _logger.warning(
                    "audit_event",
                    action=action,
                    resource=resource,
                    caller_ip=caller_ip,
                    result="rejected",
                    status_code=exc.status_code,
                )
                raise
            except Exception as exc:
                _logger.error(
                    "audit_event",
                    action=action,
                    resource=resource,
                    caller_ip=caller_ip,
                    result="error",
                    error=str(exc),
                )
                raise

        return wrapper

    return decorator


__all__ = [
    "protected_route_dependencies",
    "require_admin",
    "audit_log",
]
