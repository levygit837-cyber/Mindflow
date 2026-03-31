"""
HTTP client tool for web requests. Provides tools for making HTTP/HTTPS requests 
with proper error handling, authentication, and response processing. 
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.web_schemas import HTTP_CLIENT_SCHEMA

from ..base.tool_interface import AsyncToolInterface

_logger = get_logger(__name__)


class HttpClientTool(AsyncToolInterface):
    """
    HTTP client tool for making web requests. Provides a secure and feature-rich HTTP client 
    with support for various methods, authentication, headers, and response processing.
    """

    def __init__(self):
        super().__init__()
        self.name = "http_client"
        self.description = "HTTP client for web requests"
        self.default_timeout = 30
        self.max_response_size = 10 * 1024 * 1024  # 10MB

        self._schema = HTTP_CLIENT_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute HTTP request with comprehensive features.
        Args:
            method: HTTP method
            url: Target URL
            headers: HTTP headers
            params: Query parameters
            data: Request body data
            form_data: Form data
            timeout: Request timeout
            verify_ssl: Verify SSL certificates
            follow_redirects: Follow redirects
            max_redirects: Maximum redirects
        Returns:
            Dictionary with HTTP response data
        """
        try:
            method = kwargs["method"].upper()
            url = kwargs["url"]
            headers = kwargs.get("headers", {})
            params = kwargs.get("params", {})
            data = kwargs.get("data")
            form_data = kwargs.get("form_data")
            timeout = kwargs.get("timeout", self.default_timeout)
            verify_ssl = kwargs.get("verify_ssl", True)
            follow_redirects = kwargs.get("follow_redirects", True)
            max_redirects = kwargs.get("max_redirects", 5)

            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return self._format_result(
                    success=False,
                    error=f"Invalid URL: {url}"
                )

            # Log request start
            _logger.info(
                "http_request_started",
                method=method,
                url=url,
                timeout=timeout
            )

            # Execute request using appropriate backend
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
                    "url": url,
                    "headers": headers,
                    "params": params,
                    "timeout": timeout,
                    "verify": verify_ssl,
                    "allow_redirects": follow_redirects
                }

                # Add data
                if data:
                    request_kwargs["json"] = data
                elif form_data:
                    request_kwargs["data"] = form_data

                # Execute request
                import time
                start_time = time.time()
                
                response = session.request(**request_kwargs)
                response.raise_for_status()

                # Check response size
                content = response.text
                if len(content.encode('utf-8')) > self.max_response_size:
                    content = content[:self.max_response_size]
                    content += "\n... Response truncated due to size limit."

                elapsed = time.time() - start_time

                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": content,
                    "url": response.url,
                    "elapsed": elapsed,
                    "content_type": response.headers.get("content-type"),
                    "content_length": len(content)
                }

                _logger.info(
                    "http_request_completed",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    elapsed=elapsed
                )

                return self._format_result(success=True, result=result)

            except ImportError:
                return self._format_result(
                    success=False,
                    error="requests library not available. Install with: pip install requests"
                )

        except requests.exceptions.RequestException as e:
            _logger.error(
                "http_request_error",
                method=method,
                url=url,
                error=str(e)
            )
            return self._format_result(
                success=False,
                error=f"HTTP request failed: {str(e)}"
            )
        except Exception as e:
            _logger.error(
                "http_request_unexpected_error",
                method=method,
                url=url,
                error=str(e)
            )
            return self._format_result(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
