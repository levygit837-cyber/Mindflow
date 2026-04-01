"""Web tools - Callable pattern (Phase 2).

All tools in this module use:
- Pydantic input schemas for type safety
- CallableToolResult return type
- ToolContext for runtime state (root_dir, sandbox_mode, permissions)
- Appropriate factories (build_readonly_tool)
"""

from __future__ import annotations

import base64
import time
import urllib.parse
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.callable import CallableToolResult, ProgressCallback
from mindflow_backend.schemas.tools.callable_builder import build_readonly_tool
from mindflow_backend.schemas.tools.context import ToolContext

_logger = get_logger(__name__)


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
    """Execute HTTP request with comprehensive features.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with HTTP response data or error
    """
    MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB

    try:
        method = input.method.upper()

        # Validate URL
        parsed_url = urlparse(input.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Invalid URL: {input.url}",
                metadata={
                    "error_code": "INVALID_URL",
                    "url": input.url,
                }
            )

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
                "truncated": truncated,
                "method": method,
            }

            _logger.info(
                "http_request_completed",
                method=method,
                url=input.url,
                status_code=response.status_code,
                elapsed=elapsed
            )

            return CallableToolResult(
                data=result,
                success=True,
                metadata={
                    "operation": "http_request",
                }
            )

        except ImportError:
            return CallableToolResult(
                data=None,
                success=False,
                error="requests library not available. Install with: pip install requests",
                metadata={
                    "error_code": "MISSING_DEPENDENCY",
                    "method": method,
                    "url": input.url,
                }
            )
        except requests.exceptions.Timeout:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Request timeout after {input.timeout} seconds",
                metadata={
                    "error_code": "TIMEOUT",
                    "method": method,
                    "url": input.url,
                }
            )
        except requests.exceptions.SSLError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"SSL verification failed: {e}",
                metadata={
                    "error_code": "SSL_ERROR",
                    "method": method,
                    "url": input.url,
                }
            )
        except requests.exceptions.ConnectionError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Connection failed: {e}",
                metadata={
                    "error_code": "CONNECTION_ERROR",
                    "method": method,
                    "url": input.url,
                }
            )
        except requests.exceptions.HTTPError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"HTTP error: {e}",
                metadata={
                    "error_code": "HTTP_ERROR",
                    "method": method,
                    "url": input.url,
                    "status_code": e.response.status_code if e.response else None,
                }
            )
        except requests.exceptions.RequestException as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"HTTP request failed: {e}",
                metadata={
                    "error_code": "REQUEST_ERROR",
                    "method": method,
                    "url": input.url,
                }
            )

    except Exception as e:
        _logger.error(
            "http_request_unexpected_error",
            method=input.method,
            url=input.url,
            error=str(e)
        )
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Unexpected error: {e}",
            metadata={
                "error_code": "UNEXPECTED_ERROR",
                "method": input.method,
                "url": input.url,
            }
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
    """Scrape web page content with CSS selectors.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with scraped content or error
    """
    try:
        # Check BeautifulSoup availability
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return CallableToolResult(
                data=None,
                success=False,
                error="BeautifulSoup not available. Install with: pip install beautifulsoup4",
                metadata={
                    "error_code": "MISSING_DEPENDENCY",
                    "url": input.url,
                }
            )

        # Fetch page content using HTTP client
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            response = session.get(
                input.url,
                headers=input.headers,
                timeout=input.timeout,
                verify=True
            )
            response.raise_for_status()

        except ImportError:
            return CallableToolResult(
                data=None,
                success=False,
                error="requests library not available. Install with: pip install requests",
                metadata={
                    "error_code": "MISSING_DEPENDENCY",
                    "url": input.url,
                }
            )
        except requests.exceptions.RequestException as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Failed to fetch page: {e}",
                metadata={
                    "error_code": "FETCH_ERROR",
                    "url": input.url,
                }
            )

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data
        result = {
            "url": input.url,
            "title": soup.title.string if soup.title else "",
            "extracted_data": {},
            "links": [],
            "images": [],
            "metadata": {
                "content_type": response.headers.get("content-type"),
                "content_length": len(response.text),
                "status_code": response.status_code
            }
        }

        # Extract text content
        if input.extract_text:
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
            # Limit text size
            if len(text) > 50000:
                text = text[:50000] + "\n... Text truncated due to size limit."
            result["content"] = text

        # Extract data by selectors
        for selector in input.selectors:
            elements = soup.select(selector)
            extracted = []
            for element in elements:
                data = {
                    "text": element.get_text(strip=True),
                    "html": str(element)[:1000],  # Limit HTML size
                    "attributes": dict(element.attrs)
                }
                extracted.append(data)
            result["extracted_data"][selector] = extracted

        # Extract links
        if input.extract_links:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text(strip=True)

                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(input.url, href)

                links.append({
                    "url": absolute_url,
                    "text": text,
                    "title": link.get('title', ''),
                    "target": link.get('target', '')
                })
            result["links"] = links
            result["links_count"] = len(links)

        # Extract images
        if input.extract_images:
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                alt = img.get('alt', '')
                title = img.get('title', '')

                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(input.url, src)

                images.append({
                    "url": absolute_url,
                    "alt": alt,
                    "title": title,
                    "width": img.get('width'),
                    "height": img.get('height')
                })
            result["images"] = images
            result["images_count"] = len(images)

        return CallableToolResult(
            data=result,
            success=True,
            metadata={
                "operation": "web_scraper",
            }
        )

    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Web scraping failed: {e}",
            metadata={
                "error_code": "SCRAPING_ERROR",
                "url": input.url,
            }
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
    """Execute API request with authentication.

    Args:
        input: Validated input (Pydantic model)
        context: Tool execution context
        on_progress: Optional progress callback

    Returns:
        CallableToolResult with API response or error
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
                    return CallableToolResult(
                        data=None,
                        success=False,
                        error="Basic auth requires username and password",
                        metadata={
                            "error_code": "MISSING_CREDENTIALS",
                            "url": full_url,
                        }
                    )

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

            api_success = 200 <= response.status_code < 300

            return CallableToolResult(
                data={
                    "api_success": api_success,
                    "status_code": response.status_code,
                    "data": response_data,
                    "headers": dict(response.headers),
                    "url": response.url,
                    "method": input.method.upper(),
                },
                success=True,
                metadata={
                    "operation": "api_client",
                }
            )

        except ImportError:
            return CallableToolResult(
                data=None,
                success=False,
                error="requests library not available. Install with: pip install requests",
                metadata={
                    "error_code": "MISSING_DEPENDENCY",
                    "url": full_url,
                }
            )
        except requests.exceptions.Timeout:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"API request timeout after {input.timeout} seconds",
                metadata={
                    "error_code": "TIMEOUT",
                    "url": full_url,
                }
            )
        except requests.exceptions.ConnectionError as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"Connection failed: {e}",
                metadata={
                    "error_code": "CONNECTION_ERROR",
                    "url": full_url,
                }
            )
        except requests.exceptions.RequestException as e:
            return CallableToolResult(
                data=None,
                success=False,
                error=f"API request failed: {e}",
                metadata={
                    "error_code": "REQUEST_ERROR",
                    "url": full_url,
                }
            )

    except Exception as e:
        return CallableToolResult(
            data=None,
            success=False,
            error=f"Unexpected error: {e}",
            metadata={
                "error_code": "UNEXPECTED_ERROR",
                "api_url": input.api_url,
                "endpoint": input.endpoint,
            }
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
