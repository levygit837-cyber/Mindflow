"""HttpClientTool v3 - Adapter to the canonical HTTP client implementation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

from .http_client import HttpClientTool

_TRUNCATION_MARKER = "\n... Response truncated due to size limit."


class HttpClientInput(BaseModel):
    """Input schema for HttpClientTool v3."""

    method: str = Field(
        description="HTTP method: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS"
    )
    url: str = Field(
        description="Target URL (must include scheme: http:// or https://)"
    )
    headers: dict[str, str] = Field(
        default={},
        description="HTTP headers as key-value pairs",
    )
    params: dict[str, str] = Field(
        default={},
        description="Query parameters as key-value pairs",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Request body data (JSON)",
    )
    form_data: dict[str, str] | None = Field(
        default=None,
        description="Form data (application/x-www-form-urlencoded)",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )
    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects",
    )
    max_redirects: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Maximum number of redirects to follow",
    )


def _map_http_error_code(error_code: str | None, error: str) -> str:
    if error_code:
        return error_code
    if "Invalid URL" in error:
        return "INVALID_URL"
    if "timeout" in error.lower():
        return "TIMEOUT"
    if "SSL" in error:
        return "SSL_ERROR"
    if "Connection failed" in error:
        return "CONNECTION_ERROR"
    if "HTTP error" in error:
        return "HTTP_ERROR"
    if "No HTTP library available" in error or "No module named" in error:
        return "MISSING_DEPENDENCY"
    return "REQUEST_ERROR"


async def http_client_execute(input: HttpClientInput, context: ToolContext) -> dict[str, Any]:
    """Execute HTTP request using the canonical V1 implementation."""
    try:
        response = await HttpClientTool().execute(
            method=input.method,
            url=input.url,
            headers=input.headers,
            params=input.params,
            data=input.data,
            form_data=input.form_data,
            timeout=input.timeout,
            verify_ssl=input.verify_ssl,
            follow_redirects=input.follow_redirects,
            max_redirects=input.max_redirects,
        )
    except ImportError as exc:
        return {
            "success": False,
            "error": str(exc),
            "error_code": "MISSING_DEPENDENCY",
            "method": input.method.upper(),
            "url": input.url,
        }

    if not response["success"]:
        error = response.get("error", "HTTP request failed")
        error_result = response.get("result") or {}
        result_url = error_result.get("url", input.url)
        result = {
            "success": False,
            "error": error,
            "error_code": _map_http_error_code(response.get("error_code"), error),
            "method": input.method.upper(),
            "url": result_url,
        }
        if response.get("status_code") is not None:
            result["status_code"] = response["status_code"]
        return result

    payload = response["result"]
    body = payload["body"]
    return {
        "success": True,
        "method": input.method.upper(),
        "status_code": payload["status_code"],
        "headers": payload["headers"],
        "body": body,
        "url": payload["url"],
        "elapsed": payload["elapsed"],
        "content_type": payload["content_type"],
        "content_length": payload["content_length"],
        "truncated": body.endswith(_TRUNCATION_MARKER),
    }


HttpClientToolV3 = build_tool(
    name="http_client",
    description=(
        "HTTP client for web requests with retry logic, SSL verification, "
        "and response handling."
    ),
    input_schema=HttpClientInput,
    execute=http_client_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
