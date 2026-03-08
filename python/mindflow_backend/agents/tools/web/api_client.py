"""
API client tool for REST API interactions. Provides tools for making authenticated 
API requests with various authentication methods and response handling.
"""

from __future__ import annotations
import asyncio
import json
import base64
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType
from ..base.tool_interface import AsyncToolInterface
from ..base.tool_schemas import (
    ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter
)

_logger = get_logger(__name__)


class ApiClientTool(AsyncToolInterface):
    """
    API client tool for REST API interactions with authentication.
    """

    def __init__(self):
        super().__init__()
        self.name = "api_client"
        self.description = "REST API client with authentication and retry logic"

        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="web",
            parameters=[
                create_parameter(
                    name="api_url",
                    param_type=ParameterType.STRING,
                    description="Base API URL",
                    required=True
                ),
                create_parameter(
                    name="endpoint",
                    param_type=ParameterType.STRING,
                    description="API endpoint",
                    required=True
                ),
                create_parameter(
                    name="method",
                    param_type=ParameterType.STRING,
                    description="HTTP method",
                    required=False,
                    default="GET"
                ),
                create_parameter(
                    name="headers",
                    param_type=ParameterType.OBJECT,
                    description="API headers",
                    required=False,
                    default={}
                ),
                create_parameter(
                    name="auth_type",
                    param_type=ParameterType.STRING,
                    description="Authentication type (bearer, basic, api_key)",
                    required=False
                ),
                create_parameter(
                    name="auth_token",
                    param_type=ParameterType.STRING,
                    description="Authentication token",
                    required=False
                ),
                create_parameter(
                    name="username",
                    param_type=ParameterType.STRING,
                    description="Username for basic auth",
                    required=False
                ),
                create_parameter(
                    name="password",
                    param_type=ParameterType.STRING,
                    description="Password for basic auth",
                    required=False
                ),
                create_parameter(
                    name="api_key_header",
                    param_type=ParameterType.STRING,
                    description="API key header name",
                    required=False,
                    default="X-API-Key"
                ),
                create_parameter(
                    name="data",
                    param_type=ParameterType.OBJECT,
                    description="Request data",
                    required=False
                ),
                create_parameter(
                    name="params",
                    param_type=ParameterType.OBJECT,
                    description="Query parameters",
                    required=False,
                    default={}
                )
            ],
            returns={
                "type": "object",
                "description": "API response",
                "properties": {
                    "status_code": {"type": "integer", "description": "HTTP status code"},
                    "data": {"type": "object", "description": "Response data"},
                    "headers": {"type": "object", "description": "Response headers"},
                    "success": {"type": "boolean", "description": "Request success"}
                }
            }
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute API request with authentication.
        Args:
            api_url: Base API URL
            endpoint: API endpoint
            method: HTTP method
            headers: API headers
            auth_type: Authentication type
            auth_token: Authentication token
            username: Username for basic auth
            password: Password for basic auth
            api_key_header: API key header name
            data: Request data
            params: Query parameters
        Returns:
            Dictionary with API response
        """
        try:
            api_url = kwargs["api_url"]
            endpoint = kwargs["endpoint"]
            method = kwargs.get("method", "GET")
            headers = kwargs.get("headers", {})
            auth_type = kwargs.get("auth_type")
            auth_token = kwargs.get("auth_token")
            username = kwargs.get("username")
            password = kwargs.get("password")
            api_key_header = kwargs.get("api_key_header", "X-API-Key")
            data = kwargs.get("data")
            params = kwargs.get("params", {})

            # Construct full URL
            if not endpoint.startswith('/'):
                endpoint = '/' + endpoint
            full_url = f"{api_url.rstrip('/')}{endpoint}"

            # Prepare authentication
            auth_headers = {}
            if auth_type and auth_token:
                if auth_type.lower() == "bearer":
                    auth_headers["Authorization"] = f"Bearer {auth_token}"
                elif auth_type.lower() == "api_key":
                    auth_headers[api_key_header] = auth_token
                elif auth_type.lower() == "basic" and username and password:
                    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                    auth_headers["Authorization"] = f"Basic {credentials}"

            # Merge headers
            final_headers = {**headers, **auth_headers}

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
                    "method": method,
                    "url": full_url,
                    "headers": final_headers,
                    "params": params,
                    "timeout": 30
                }

                # Add data
                if data:
                    request_kwargs["json"] = data

                # Execute request
                response = session.request(**request_kwargs)

                # Try to parse JSON response
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text

                success = 200 <= response.status_code < 300

                return self._format_result(
                    success=True,
                    result={
                        "status_code": response.status_code,
                        "data": response_data,
                        "headers": dict(response.headers),
                        "url": response.url,
                        "success": success
                    }
                )

            except ImportError:
                return self._format_result(
                    success=False,
                    error="requests library not available. Install with: pip install requests"
                )

        except Exception as e:
            return self._format_result(
                success=False,
                error=f"API request failed: {str(e)}"
            )

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
