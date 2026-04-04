"""ApiClientTool v3 - Adapter to the canonical API client implementation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

from .api_client import ApiClientTool


class ApiClientInput(BaseModel):
    """Input schema for ApiClientTool v3."""

    api_url: str = Field(
        description="Base API URL (e.g., https://api.example.com)"
    )
    endpoint: str = Field(
        description="API endpoint path (e.g., /users or users)"
    )
    method: str = Field(
        default="GET",
        description="HTTP method: GET, POST, PUT, DELETE, PATCH",
    )
    headers: dict[str, str] = Field(
        default={},
        description="Additional HTTP headers",
    )
    auth_type: str | None = Field(
        default=None,
        description="Authentication type: 'bearer', 'api_key', 'basic'",
    )
    auth_token: str | None = Field(
        default=None,
        description="Authentication token (for bearer or api_key)",
    )
    username: str | None = Field(
        default=None,
        description="Username (for basic auth)",
    )
    password: str | None = Field(
        default=None,
        description="Password (for basic auth)",
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Request body data (JSON)",
    )
    params: dict[str, str] = Field(
        default={},
        description="Query parameters",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )


def _map_api_error_code(error_code: str | None, error: str) -> str:
    if error_code:
        return error_code
    if "Basic auth requires username and password" in error:
        return "MISSING_CREDENTIALS"
    if "timeout" in error.lower():
        return "TIMEOUT"
    if "Connection failed" in error:
        return "CONNECTION_ERROR"
    if "No HTTP library available" in error or "No module named" in error:
        return "MISSING_DEPENDENCY"
    return "REQUEST_ERROR"


async def api_client_execute(input: ApiClientInput, context: ToolContext) -> dict[str, Any]:
    """Execute API request using the canonical V1 implementation."""
    full_url = f"{input.api_url.rstrip('/')}/{input.endpoint.lstrip('/')}"

    try:
        response = await ApiClientTool().execute(
            api_url=input.api_url,
            endpoint=input.endpoint,
            method=input.method,
            headers=input.headers,
            auth_type=input.auth_type,
            auth_token=input.auth_token,
            username=input.username,
            password=input.password,
            api_key_header=input.api_key_header,
            data=input.data,
            params=input.params,
            timeout=input.timeout,
        )
    except ImportError as exc:
        return {
            "success": False,
            "error": str(exc),
            "error_code": "MISSING_DEPENDENCY",
            "url": full_url,
        }

    if not response["success"]:
        error = response.get("error", "API request failed")
        return {
            "success": False,
            "error": error,
            "error_code": _map_api_error_code(response.get("error_code"), error),
            "url": full_url,
        }

    payload = response["result"]
    return {
        "success": True,
        "api_success": payload["success"],
        "status_code": payload["status_code"],
        "data": payload["data"],
        "headers": payload["headers"],
        "url": payload["url"],
        "method": input.method.upper(),
    }


ApiClientToolV3 = build_tool(
    name="api_client",
    description=(
        "REST API client with authentication support. "
        "Supports Bearer token, API key, and Basic authentication. "
        "Includes automatic retry logic for transient failures and "
        "JSON response parsing. Ideal for interacting with REST APIs."
    ),
    input_schema=ApiClientInput,
    execute=api_client_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
