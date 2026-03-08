"""
HTTP client tool for web requests. Provides tools for making HTTP/HTTPS requests 
with proper error handling, authentication, and response processing. 
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from ..base.tool_interface import AsyncToolInterface
from ..base.tool_schemas import (
    ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter
)

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

        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="web",
            parameters=[
                create_parameter(
                    name="method",
                    param_type=ParameterType.STRING,
                    description="HTTP method (GET, POST, PUT, DELETE, PATCH)",
                    required=True
                ),
                create_parameter(
                    name="url",
                    param_type=ParameterType.STRING,
                    description="Target URL",
                    required=True
                ),
                create_parameter(
                    name="headers",
                    param_type=ParameterType.OBJECT,
                    description="HTTP headers",
                    required=False,
                    default={}
                ),
                create_parameter(
                    name="params",
                    param_type=ParameterType.OBJECT,
                    description="Query parameters",
                    required=False,
                    default={}
                ),
                create_parameter(
                    name="data",
                    param_type=ParameterType.OBJECT,
                    description="Request body data (JSON)",
                    required=False
                ),
                create_parameter(
                    name="form_data",
                    param_type=ParameterType.OBJECT,
                    description="Form data",
                    required=False
                ),
                create_parameter(
                    name="timeout",
                    param_type=ParameterType.INTEGER,
                    description="Request timeout in seconds",
                    required=False,
                    default=30
                ),
                create_parameter(
                    name="verify_ssl",
                    param_type=ParameterType.BOOLEAN,
                    description="Verify SSL certificates",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="follow_redirects",
                    param_type=ParameterType.BOOLEAN,
                    description="Follow HTTP redirects",
                    required=False,
                    default=True
                ),
                create_parameter(
                    name="max_redirects",
                    param_type=ParameterType.INTEGER,
                    description="Maximum redirects to follow",
                    required=False,
                    default=5
                )
            ],
            returns={
                "type": "object",
                "description": "HTTP response data",
                "properties": {
                    "status_code": {"type": "integer", "description": "HTTP status code"},
                    "headers": {"type": "object", "description": "Response headers"},
                    "body": {"type": "string", "description": "Response body"},
                    "url": {"type": "string", "description": "Final URL after redirects"},
                    "elapsed": {"type": "float", "description": "Request time in seconds"},
                    "content_type": {"type": "string", "description": "Response content type"},
                    "content_length": {"type": "integer", "description": "Response content length"}
                }
            }
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
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

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
