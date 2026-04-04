"""
API client tool for REST API interactions.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from mindflow_backend.schemas.tools.web_schemas import API_CLIENT_SCHEMA

from ..base.tool_interface import AsyncToolInterface
from .http_client import HttpClientTool


class ApiClientTool(AsyncToolInterface):
    """
    API client tool for REST API interactions with authentication.
    """

    def __init__(self, backend: Any | None = None):
        super().__init__()
        self.backend = backend
        self.name = "api_client"
        self.description = "REST API client with authentication and retry logic"
        self._schema = API_CLIENT_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute API request with authentication.
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
            timeout = kwargs.get("timeout", 30)
            verify_ssl = kwargs.get("verify_ssl", True)
            follow_redirects = kwargs.get("follow_redirects", True)
            max_redirects = kwargs.get("max_redirects", 5)

            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint
            full_url = f"{api_url.rstrip('/')}{endpoint}"

            auth_headers: dict[str, str] = {}
            if auth_type:
                normalized_auth_type = auth_type.lower()
                if normalized_auth_type == "bearer" and auth_token:
                    auth_headers["Authorization"] = f"Bearer {auth_token}"
                elif normalized_auth_type == "api_key" and auth_token:
                    auth_headers[api_key_header] = auth_token
                elif normalized_auth_type == "basic":
                    if not username or not password:
                        result = self._format_result(
                            success=False,
                            error="Basic auth requires username and password",
                        )
                        result["error_code"] = "MISSING_CREDENTIALS"
                        return result
                    credentials = base64.b64encode(
                        f"{username}:{password}".encode()
                    ).decode()
                    auth_headers["Authorization"] = f"Basic {credentials}"

            response = await HttpClientTool(backend=self.backend).execute(
                method=method,
                url=full_url,
                headers={**headers, **auth_headers},
                data=data,
                params=params,
                timeout=timeout,
                verify_ssl=verify_ssl,
                follow_redirects=follow_redirects,
                max_redirects=max_redirects,
            )

            if not response["success"]:
                return response

            body = response["result"]["body"]
            try:
                response_data = json.loads(body)
            except json.JSONDecodeError:
                response_data = body

            return self._format_result(
                success=True,
                result={
                    "status_code": response["result"]["status_code"],
                    "data": response_data,
                    "headers": response["result"]["headers"],
                    "url": response["result"]["url"],
                    "success": 200 <= response["result"]["status_code"] < 300,
                },
            )
        except Exception as exc:
            result = self._format_result(
                success=False,
                error=f"API request failed: {str(exc)}",
            )
            result["error_code"] = "REQUEST_ERROR"
            return result

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
