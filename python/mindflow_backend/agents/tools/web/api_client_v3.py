"""ApiClientTool v3 - New Tool System Implementation.

REST API client with authentication support (Bearer, API Key, Basic Auth).
"""

from __future__ import annotations

import base64
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


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
        description="HTTP method: GET, POST, PUT, DELETE, PATCH"
    )
    headers: dict[str, str] = Field(
        default={},
        description="Additional HTTP headers"
    )
    auth_type: str | None = Field(
        default=None,
        description="Authentication type: 'bearer', 'api_key', 'basic'"
    )
    auth_token: str | None = Field(
        default=None,
        description="Authentication token (for bearer or api_key)"
    )
    username: str | None = Field(
        default=None,
        description="Username (for basic auth)"
    )
    password: str | None = Field(
        default=None,
        description="Password (for basic auth)"
    )
    api_key_header: str = Field(
        default="X-API-Key",
        description="Header name for API key authentication"
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Request body data (JSON)"
    )
    params: dict[str, str] = Field(
        default={},
        description="Query parameters"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def api_client_execute(input: ApiClientInput, context: ToolContext) -> dict[str, Any]:
    """Execute API request with authentication.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with API response or error
    """
    try:
        # Construct full URL
        endpoint = input.endpoint
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        full_url = f"{input.api_url.rstrip('/')}{endpoint}"

        # Prepare authentication
        auth_headers = {}
        if input.auth_type and input.auth_token:
            auth_type_lower = input.auth_type.lower()

            if auth_type_lower == "bearer":
                auth_headers["Authorization"] = f"Bearer {input.auth_token}"
            elif auth_type_lower == "api_key":
                auth_headers[input.api_key_header] = input.auth_token
            elif auth_type_lower == "basic":
                if input.username and input.password:
                    credentials = base64.b64encode(
                        f"{input.username}:{input.password}".encode()
                    ).decode()
                    auth_headers["Authorization"] = f"Basic {credentials}"
                else:
                    return {
                        "success": False,
                        "error": "Basic auth requires username and password",
                        "error_code": "MISSING_CREDENTIALS",
                        "url": full_url
                    }

        # Merge headers
        final_headers = {**input.headers, **auth_headers}

        # Execute request
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            # Prepare session with retry strategy
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # Prepare request arguments
            request_kwargs = {
                "method": input.method.upper(),
                "url": full_url,
                "headers": final_headers,
                "params": input.params,
                "timeout": input.timeout
            }

            # Add data
            if input.data:
                request_kwargs["json"] = input.data

            # Execute request
            response = session.request(**request_kwargs)

            # Try to parse JSON response
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            success = 200 <= response.status_code < 300

            return {
                "success": True,
                "api_success": success,
                "status_code": response.status_code,
                "data": response_data,
                "headers": dict(response.headers),
                "url": response.url,
                "method": input.method.upper()
            }

        except ImportError:
            return {
                "success": False,
                "error": "requests library not available. Install with: pip install requests",
                "error_code": "MISSING_DEPENDENCY",
                "url": full_url
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"API request timeout after {input.timeout} seconds",
                "error_code": "TIMEOUT",
                "url": full_url
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection failed: {e}",
                "error_code": "CONNECTION_ERROR",
                "url": full_url
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"API request failed: {e}",
                "error_code": "REQUEST_ERROR",
                "url": full_url
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR",
            "api_url": input.api_url,
            "endpoint": input.endpoint
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


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
