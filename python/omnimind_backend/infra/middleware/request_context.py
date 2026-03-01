"""Request context middleware — X-Request-ID generation and propagation.

Assigns a unique request ID to every incoming request and stores it in a
``ContextVar`` so that loggers, downstream services, and response headers
can reference it for distributed tracing / correlation.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)

# ContextVar accessible throughout the async call-stack.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request ID (empty string outside a request)."""
    return request_id_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Generate / propagate ``X-Request-ID`` and log basic request timing."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Honour an existing X-Request-ID from the caller (gateway/load-balancer),
        # otherwise generate a new one.
        incoming_id = request.headers.get("X-Request-ID")
        req_id = incoming_id or f"req-{uuid.uuid4()}"

        token = request_id_var.set(req_id)
        start = time.perf_counter()

        try:
            _logger.info(
                "request_start",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                },
            )

            response = await call_next(request)

            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Request-ID"] = req_id

            _logger.info(
                "request_end",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response
        finally:
            request_id_var.reset(token)
