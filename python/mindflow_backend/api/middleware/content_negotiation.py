"""HTTP content negotiation and content-type enforcement middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mindflow_backend.infra.config import get_settings

_BODY_METHODS = {"POST", "PUT", "PATCH"}
_SSE_SUFFIXES = ("/stream", "/events", "/chat")
_JSON_MEDIA_TYPES = ("application/json", "application/merge-patch+json")


def _has_body(request: Request) -> bool:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            return int(content_length) > 0
        except ValueError:
            return True
    return "content-type" in request.headers


def _accepts_json(accept: str) -> bool:
    return not accept or "*/*" in accept or "application/json" in accept


def _accepts_sse(accept: str) -> bool:
    return "text/event-stream" in accept or "*/*" in accept or not accept


def _is_stream_path(path: str) -> bool:
    return path.endswith(_SSE_SUFFIXES) or "/stream/" in path


class ContentNegotiationMiddleware(BaseHTTPMiddleware):
    """Reject unsupported request and response media types early."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()
        path = request.url.path
        method = request.method.upper()
        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()

        if settings.security_require_json_content_type and method in _BODY_METHODS and _has_body(request):
            if content_type and content_type not in _JSON_MEDIA_TYPES:
                return JSONResponse(
                    status_code=415,
                    content={"detail": "Unsupported Content-Type. Use application/json."},
                )

        if settings.security_enforce_accept_header:
            if _is_stream_path(path):
                if not _accepts_sse(accept):
                    return JSONResponse(
                        status_code=406,
                        content={"detail": "Not acceptable. Use Accept: text/event-stream."},
                    )
            elif not _accepts_json(accept):
                return JSONResponse(
                    status_code=406,
                    content={"detail": "Not acceptable. Use Accept: application/json."},
                )

        response = await call_next(request)
        response.headers.setdefault("Vary", "Accept")
        return response
