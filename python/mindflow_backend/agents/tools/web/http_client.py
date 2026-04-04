"""
HTTP client tool for web requests.
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tools.web_schemas import HTTP_CLIENT_SCHEMA

from ..base.tool_interface import AsyncToolInterface

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None
    HTTPAdapter = None
    Retry = None

_logger = get_logger(__name__)
_TRUNCATION_MARKER = "\n... Response truncated due to size limit."


class HttpClientTool(AsyncToolInterface):
    """
    HTTP client tool for making web requests.
    """

    def __init__(self, backend: Any | None = None):
        super().__init__()
        self.backend = backend
        self.name = "http_client"
        self.description = "HTTP client for web requests"
        self.default_timeout = 30
        self.max_response_size = 10 * 1024 * 1024
        self._schema = HTTP_CLIENT_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        """
        Execute an HTTP request with optional redirects, SSL validation, and retries.
        """
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

        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return self._format_error_result(
                error=f"Invalid URL: {url}",
                error_code="INVALID_URL",
            )

        _logger.info(
            "http_request_started",
            method=method,
            url=url,
            timeout=timeout,
        )

        try:
            if requests is not None:
                result = await self._execute_requests(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    form_data=form_data,
                    timeout=timeout,
                    verify_ssl=verify_ssl,
                    follow_redirects=follow_redirects,
                    max_redirects=max_redirects,
                )
            elif aiohttp is not None:
                result = await self._execute_aiohttp(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    form_data=form_data,
                    timeout=timeout,
                    verify_ssl=verify_ssl,
                    follow_redirects=follow_redirects,
                    max_redirects=max_redirects,
                )
            else:
                return self._format_error_result(
                    error="No HTTP library available. Install aiohttp or requests.",
                    error_code="MISSING_DEPENDENCY",
                )

            if result["success"]:
                payload = result["result"]
                _logger.info(
                    "http_request_completed",
                    method=method,
                    url=url,
                    status_code=payload["status_code"],
                    elapsed=payload["elapsed"],
                )
            return result
        except Exception as exc:
            _logger.error(
                "http_request_error",
                method=method,
                url=url,
                error=str(exc),
            )
            return self._format_error_result(
                error=self._normalize_error_message(exc),
                error_code=self._classify_error_code(exc),
                status_code=getattr(getattr(exc, "response", None), "status_code", None),
            )

    async def _execute_aiohttp(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, Any],
        params: dict[str, Any],
        data: Any,
        form_data: Any,
        timeout: int,
        verify_ssl: bool,
        follow_redirects: bool,
        max_redirects: int,
    ) -> dict[str, Any]:
        started_at = time.time()
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        request_kwargs: dict[str, Any] = {
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "timeout": timeout_obj,
            "ssl": None if verify_ssl else False,
            "allow_redirects": follow_redirects,
            "max_redirects": max_redirects,
        }

        if data is not None:
            request_kwargs["json"] = data
        elif form_data is not None:
            request_kwargs["data"] = form_data

        async with aiohttp.ClientSession() as session, session.request(
            **request_kwargs
        ) as response:
            response.raise_for_status()
            content = await response.text()
            status_code = response.status
            response_headers = dict(response.headers)
            response_url = str(response.url)
            content_type = response.headers.get("content-type")

        return self._format_result(
            success=True,
            result=self._build_response_payload(
                status_code=status_code,
                headers=response_headers,
                body=content,
                url=response_url,
                elapsed=time.time() - started_at,
                content_type=content_type,
            ),
        )

    async def _execute_requests(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, Any],
        params: dict[str, Any],
        data: Any,
        form_data: Any,
        timeout: int,
        verify_ssl: bool,
        follow_redirects: bool,
        max_redirects: int,
    ) -> dict[str, Any]:
        session = requests.Session()
        started_at = time.time()
        try:
            if Retry is not None and HTTPAdapter is not None:
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)

            session.max_redirects = max_redirects
            request_kwargs: dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
                "verify": verify_ssl,
                "allow_redirects": follow_redirects,
            }

            if data is not None:
                request_kwargs["json"] = data
            elif form_data is not None:
                request_kwargs["data"] = form_data

            request_executor = getattr(session, method.lower(), None)
            if callable(request_executor):
                request_kwargs.pop("method")
                response = request_executor(**request_kwargs)
            else:
                response = session.request(**request_kwargs)
            response.raise_for_status()
            content = response.text

            return self._format_result(
                success=True,
                result=self._build_response_payload(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=content,
                    url=response.url,
                    elapsed=time.time() - started_at,
                    content_type=response.headers.get("content-type"),
                ),
            )
        finally:
            session.close()

    def _build_response_payload(
        self,
        *,
        status_code: int,
        headers: dict[str, Any],
        body: str,
        url: str,
        elapsed: float,
        content_type: str | None,
    ) -> dict[str, Any]:
        if len(body.encode("utf-8")) > self.max_response_size:
            body = body[: self.max_response_size]
            body += _TRUNCATION_MARKER

        return {
            "status_code": status_code,
            "headers": headers,
            "body": body,
            "url": url,
            "elapsed": elapsed,
            "content_type": content_type,
            "content_length": len(body),
        }

    def _classify_error_code(self, exc: Exception) -> str:
        if requests is not None:
            if isinstance(exc, requests.exceptions.Timeout):
                return "TIMEOUT"
            if isinstance(exc, requests.exceptions.SSLError):
                return "SSL_ERROR"
            if isinstance(exc, requests.exceptions.ConnectionError):
                return "CONNECTION_ERROR"
            if isinstance(exc, requests.exceptions.HTTPError):
                return "HTTP_ERROR"
            if isinstance(exc, requests.exceptions.RequestException):
                return "REQUEST_ERROR"

        if aiohttp is not None:
            if isinstance(exc, TimeoutError | aiohttp.ServerTimeoutError):
                return "TIMEOUT"
            if isinstance(exc, aiohttp.ClientConnectorSSLError):
                return "SSL_ERROR"
            if isinstance(exc, aiohttp.ClientConnectionError):
                return "CONNECTION_ERROR"
            if isinstance(exc, aiohttp.ClientResponseError):
                return "HTTP_ERROR"
            if isinstance(exc, aiohttp.ClientError):
                return "REQUEST_ERROR"

        return "REQUEST_ERROR"

    def _normalize_error_message(self, exc: Exception) -> str:
        error_code = self._classify_error_code(exc)

        if error_code == "TIMEOUT":
            return "Request timeout after configured timeout"
        if error_code == "SSL_ERROR":
            return f"SSL verification failed: {exc}"
        if error_code == "CONNECTION_ERROR":
            return f"Connection failed: {exc}"
        if error_code == "HTTP_ERROR":
            return f"HTTP error: {exc}"
        return f"HTTP request failed: {exc}"

    def _format_error_result(
        self,
        *,
        error: str,
        error_code: str,
        status_code: int | None = None,
    ) -> dict[str, Any]:
        result = self._format_result(success=False, error=error)
        result["error_code"] = error_code
        if status_code is not None:
            result["status_code"] = status_code
        return result

    def get_schema(self) -> dict[str, Any]:
        """
        Get tool schema.
        """
        return self._schema.dict()
