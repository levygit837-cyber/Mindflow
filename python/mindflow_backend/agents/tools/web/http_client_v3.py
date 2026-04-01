"""HttpClientTool v3 - New Tool System Implementation.

HTTP client for web requests with retry logic, SSL verification, and response handling.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools import build_tool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input Schema
# ---------------------------------------------------------------------------


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
        description="HTTP headers as key-value pairs"
    )
    params: dict[str, str] = Field(
        default={},
        description="Query parameters as key-value pairs"
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Request body data (JSON)"
    )
    form_data: dict[str, str] | None = Field(
        default=None,
        description="Form data (application/x-www-form-urlencoded)"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates"
    )
    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects"
    )
    max_redirects: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Maximum number of redirects to follow"
    )


# ---------------------------------------------------------------------------
# Execute Function
# ---------------------------------------------------------------------------


async def http_client_execute(input: HttpClientInput, context: ToolContext) -> dict[str, Any]:
    """Execute HTTP request with comprehensive features.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context

    Returns:
        Dictionary with HTTP response data or error
    """
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

    try:
        method = input.method.upper()

        # Validate URL
        parsed_url = urlparse(input.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return {
                "success": False,
                "error": f"Invalid URL: {input.url}",
                "error_code": "INVALID_URL",
                "url": input.url
            }

        # Log request start
        _logger.info(
            "http_request_started",
            method=method,
            url=input.url,
            timeout=input.timeout
        )

        # Execute request using requests library
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
                "method": method,
                "url": input.url,
                "headers": input.headers,
                "params": input.params,
                "timeout": input.timeout,
                "verify": input.verify_ssl,
                "allow_redirects": input.follow_redirects
            }

            # Add data
            if input.data:
                request_kwargs["json"] = input.data
            elif input.form_data:
                request_kwargs["data"] = input.form_data

            # Execute request
            start_time = time.time()
            response = session.request(**request_kwargs)
            response.raise_for_status()

            # Check response size
            content = response.text
            truncated = False
            if len(content.encode('utf-8')) > MAX_RESPONSE_SIZE:
                content = content[:MAX_RESPONSE_SIZE]
                content += "\n... Response truncated due to size limit."
                truncated = True

            elapsed = time.time() - start_time

            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": content,
                "url": response.url,
                "elapsed": elapsed,
                "content_type": response.headers.get("content-type"),
                "content_length": len(content),
                "truncated": truncated
            }

            _logger.info(
                "http_request_completed",
                method=method,
                url=input.url,
                status_code=response.status_code,
                elapsed=elapsed
            )

            return {
                "success": True,
                "method": method,
                **result
            }

        except ImportError:
            return {
                "success": False,
                "error": "requests library not available. Install with: pip install requests",
                "error_code": "MISSING_DEPENDENCY",
                "method": method,
                "url": input.url
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Request timeout after {input.timeout} seconds",
                "error_code": "TIMEOUT",
                "method": method,
                "url": input.url
            }
        except requests.exceptions.SSLError as e:
            return {
                "success": False,
                "error": f"SSL verification failed: {e}",
                "error_code": "SSL_ERROR",
                "method": method,
                "url": input.url
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection failed: {e}",
                "error_code": "CONNECTION_ERROR",
                "method": method,
                "url": input.url
            }
        except requests.exceptions.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP error: {e}",
                "error_code": "HTTP_ERROR",
                "method": method,
                "url": input.url,
                "status_code": e.response.status_code if e.response else None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"HTTP request failed: {e}",
                "error_code": "REQUEST_ERROR",
                "method": method,
                "url": input.url
            }

    except Exception as e:
        _logger.error(
            "http_request_unexpected_error",
            method=input.method,
            url=input.url,
            error=str(e)
        )
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "error_code": "UNEXPECTED_ERROR",
            "method": input.method,
            "url": input.url
        }


# ---------------------------------------------------------------------------
# Build Tool
# ---------------------------------------------------------------------------


HttpClientToolV3 = build_tool(
    name="http_client",
    description=(
        "HTTP client for web requests with advanced features. "
        "Supports all HTTP methods, custom headers, query parameters, JSON/form data, "
        "SSL verification, redirect handling, and automatic retry on transient failures. "
        "Includes response size limits and comprehensive error handling."
    ),
    input_schema=HttpClientInput,
    execute=http_client_execute,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
)
