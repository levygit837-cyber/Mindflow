"""Web tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_readonly_tool)
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.filesystem._legacy_adapter import (
    build_legacy_tool,
    flatten_legacy_result,
)
from mindflow_backend.agents.tools.web.api_client import ApiClientTool
from mindflow_backend.agents.tools.web.http_client import HttpClientTool
from mindflow_backend.agents.tools.web.web_scraper import WebScraperTool
from mindflow_backend.schemas.tools import (
    CallableToolResult,
    ProgressCallback,
    build_readonly_tool,
)
from mindflow_backend.schemas.tools.context import ToolContext


def _callable_result_from_flattened(
    flattened: dict[str, Any],
    *,
    metadata: dict[str, Any] | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Convert a flattened legacy result to a callable tool result."""
    if flattened.get("success"):
        data = dict(flattened)
        data.pop("success", None)
        return CallableToolResult(data=data, success=True, metadata=metadata or {})

    result_metadata = dict(metadata or {})
    error_code = flattened.get("error_code")
    if error_code:
        result_metadata.setdefault("error_code", error_code)
    return CallableToolResult(
        data=None,
        success=False,
        error=flattened.get("error") or "Unknown error",
        metadata=result_metadata,
    )


# ---------------------------------------------------------------------------
# HttpClientCallable - Priority 4
# ---------------------------------------------------------------------------


class HttpClientInput(BaseModel):
    """Input schema for HttpClientCallable."""

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


async def http_client_impl(
    input: HttpClientInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute an HTTP request through the canonical web tool."""
    tool = build_legacy_tool(HttpClientTool, context)
    result = await tool.execute(
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
    flattened = flatten_legacy_result(
        result,
        error_map={
            "invalid url": "INVALID_URL",
            "no http library available": "MISSING_DEPENDENCY",
            "timeout": "TIMEOUT",
            "ssl": "SSL_ERROR",
            "certificate": "SSL_ERROR",
            "connection failed": "CONNECTION_ERROR",
        },
        default_error_code="REQUEST_ERROR",
    )
    if flattened.get("success"):
        flattened.setdefault("method", input.method.upper())
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "http_request"},
    )


HttpClientCallable = build_readonly_tool(
    name="http_client",
    description=(
        "HTTP client for web requests with advanced features. "
        "Supports all HTTP methods, custom headers, query parameters, JSON/form data, "
        "SSL verification, redirect handling, and automatic retry on transient failures. "
        "Includes response size limits and comprehensive error handling. "
        "Concurrent-safe: can make multiple HTTP requests in parallel."
    ),
    input_schema=HttpClientInput,
    call_fn=http_client_impl,
    is_concurrency_safe=True,  # Safe to make multiple HTTP requests in parallel
    interrupt_behavior="cancel",  # Safe to interrupt HTTP requests
)


# ---------------------------------------------------------------------------
# WebScraperCallable - Priority 4
# ---------------------------------------------------------------------------


class WebScraperInput(BaseModel):
    """Input schema for WebScraperCallable."""

    url: str = Field(
        description="URL to scrape"
    )
    selectors: list[str] = Field(
        default=[],
        description="CSS selectors to extract specific elements"
    )
    headers: dict[str, str] = Field(
        default={},
        description="HTTP headers for the request"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds"
    )
    extract_links: bool = Field(
        default=False,
        description="Extract all links from the page"
    )
    extract_images: bool = Field(
        default=False,
        description="Extract all images from the page"
    )
    extract_text: bool = Field(
        default=True,
        description="Extract clean text content from the page"
    )


async def web_scraper_impl(
    input: WebScraperInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Scrape web content through the canonical web scraper."""
    tool = build_legacy_tool(WebScraperTool, context)
    result = await tool.execute(
        url=input.url,
        selectors=input.selectors,
        headers=input.headers,
        timeout=input.timeout,
        extract_links=input.extract_links,
        extract_images=input.extract_images,
        extract_text=input.extract_text,
    )
    flattened = flatten_legacy_result(
        result,
        error_map={
            "no http library available": "MISSING_DEPENDENCY",
            "requests library not available": "MISSING_DEPENDENCY",
            "invalid url": "FETCH_ERROR",
            "http request failed": "FETCH_ERROR",
            "failed to fetch page": "FETCH_ERROR",
        },
        default_error_code="SCRAPING_ERROR",
    )
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "web_scraper"},
    )


WebScraperCallable = build_readonly_tool(
    name="web_scraper",
    description=(
        "Web scraping tool with CSS selector support. "
        "Extracts page title, clean text content, specific elements via CSS selectors, "
        "links, and images. Converts relative URLs to absolute. "
        "Includes automatic retry and size limits for large pages. "
        "Concurrent-safe: can scrape multiple pages in parallel."
    ),
    input_schema=WebScraperInput,
    call_fn=web_scraper_impl,
    is_concurrency_safe=True,  # Safe to scrape multiple pages in parallel
    interrupt_behavior="cancel",  # Safe to interrupt web scraping
)


# ---------------------------------------------------------------------------
# ApiClientCallable - Priority 4
# ---------------------------------------------------------------------------


class ApiClientInput(BaseModel):
    """Input schema for ApiClientCallable."""

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


async def api_client_impl(
    input: ApiClientInput,
    context: ToolContext,
    on_progress: ProgressCallback | None = None,
) -> CallableToolResult[dict[str, Any]]:
    """Execute an authenticated API request through the canonical tool."""
    tool = build_legacy_tool(ApiClientTool, context)
    result = await tool.execute(
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
    flattened = flatten_legacy_result(
        result,
        error_map={
            "basic auth requires username and password": "MISSING_CREDENTIALS",
            "requests library not available": "MISSING_DEPENDENCY",
            "timeout": "TIMEOUT",
            "connection failed": "CONNECTION_ERROR",
        },
        default_error_code="REQUEST_ERROR",
    )
    return _callable_result_from_flattened(
        flattened,
        metadata={"operation": "api_client"},
    )


ApiClientCallable = build_readonly_tool(
    name="api_client",
    description=(
        "REST API client with authentication support. "
        "Supports Bearer token, API key, and Basic authentication. "
        "Includes automatic retry logic for transient failures and "
        "JSON response parsing. Ideal for interacting with REST APIs. "
        "Concurrent-safe: can make multiple API requests in parallel."
    ),
    input_schema=ApiClientInput,
    call_fn=api_client_impl,
    is_concurrency_safe=True,  # Safe to make multiple API requests in parallel
    interrupt_behavior="cancel",  # Safe to interrupt API requests
)
