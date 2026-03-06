"""Security headers middleware — Helmet-equivalent for FastAPI.

Adds defensive HTTP headers to every response to mitigate common
web-based attacks (clickjacking, MIME sniffing, XSS, etc.).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from mindflow_backend.infra.config import get_settings

# Headers applied to every response.
_COMMON_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'",
}

# Only applied in production to avoid breaking local dev workflows.
_PRODUCTION_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects security-related HTTP headers into all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        for key, value in _COMMON_HEADERS.items():
            response.headers[key] = value

        settings = get_settings()
        if settings.app_env == "production":
            for key, value in _PRODUCTION_HEADERS.items():
                response.headers[key] = value

        return response
