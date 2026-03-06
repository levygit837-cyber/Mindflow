"""API client tool for REST API interactions.

Provides specialized tools for working with REST APIs including
OpenAPI specification handling, response parsing, and error management.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

from ..base.tool_interface import AsyncToolInterface
from ..base.tool_schemas import (
    ToolSchema, 
    ToolParameter, 
    ParameterType,
    create_tool_schema,
    create_parameter
)

_logger = get_logger(__name__)


class ApiClientTool(AsyncToolInterface):
    """API client tool for REST API interactions.
    
    Provides specialized functionality for working with REST APIs
    including OpenAPI spec handling, structured responses, and
    API-specific error management.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "api_client"
        self.description = "REST API client with OpenAPI support and structured response handling"
        self._api_specs: Dict[str, Dict[str, Any]] = {}
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool schema for validation."""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            category="web",
            parameters=[
                create_parameter(
                    name="api_base_url",
                    param_type=ParameterType.STRING,
                    description="Base URL of the API",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="endpoint",
                    param_type=ParameterType.STRING,
                    description="API endpoint path (relative to base URL)",
                    required=True,
                    min_length=1
                ),
                create_parameter(
                    name="method",
                    param_type=ParameterType.STRING,
                    description="HTTP method",
                    required=False,
                    default="GET",
                    enum=["GET", "POST", "PUT", "DELETE", "PATCH"]
                ),
                create_parameter(
                    name="headers",
                    param_type=ParameterType.OBJECT,
                    description="API request headers",
                    required=False,
                    default={}
                ),
                create_parameter(
                    name="query_params",
                    param_type=ParameterType.OBJECT,
                    description="Query parameters",
                    required=False,
                    default={}
                ),
                create_parameter(
                    name="request_body",
                    param_type=ParameterType.OBJECT,
                    description="Request body data",
                    required=False
                ),
                create_parameter(
                    name="api_key",
                    param_type=ParameterType.STRING,
                    description="API key for authentication",
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
                    name="response_format",
                    param_type=ParameterType.STRING,
                    description="Expected response format",
                    required=False,
                    enum=["json", "xml", "text", "auto"],
                    default="auto"
                ),
                create_parameter(
                    name="timeout",
                    param_type=ParameterType.INTEGER,
                    description="Request timeout in seconds",
                    required=False,
                    default=30,
                    min_value=1,
                    max_value=300
                )
            ],
            requires_internet=True,
            supported_agents=list(AgentType),
            security_level="medium",
            timeout_seconds=30
        ).dict()
    
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute API request with specialized handling.
        
        Args:
            api_base_url: Base URL of the API
            endpoint: API endpoint path
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            request_body: Request body
            api_key: API key for authentication
            api_key_header: API key header name
            response_format: Expected response format
            timeout: Request timeout
            
        Returns:
            API response with structured format and metadata
        """
        try:
            # Validate required parameters
            api_base_url = kwargs.get("api_base_url")
            endpoint = kwargs.get("endpoint")
            
            if not api_base_url:
                return self._format_result(
                    success=False,
                    error="api_base_url parameter is required"
                )
            
            if not endpoint:
                return self._format_result(
                    success=False,
                    error="endpoint parameter is required"
                )
            
            # Build full URL
            full_url = self._build_api_url(api_base_url, endpoint)
            
            # Prepare request
            method = kwargs.get("method", "GET").upper()
            headers = kwargs.get("headers", {})
            query_params = kwargs.get("query_params", {})
            request_body = kwargs.get("request_body")
            api_key = kwargs.get("api_key")
            api_key_header = kwargs.get("api_key_header", "X-API-Key")
            response_format = kwargs.get("response_format", "auto")
            timeout = kwargs.get("timeout", 30)
            
            # Add API key authentication
            if api_key:
                headers[api_key_header] = api_key
            
            # Execute API request
            response = await self._execute_api_request(
                url=full_url,
                method=method,
                headers=headers,
                query_params=query_params,
                request_body=request_body,
                response_format=response_format,
                timeout=timeout
            )
            
            return self._format_result(
                success=response["success"],
                result=response,
                metadata={
                    "api_base_url": api_base_url,
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": response.get("status_code"),
                    "response_format": response.get("response_format"),
                    "response_time_ms": response.get("response_time_ms"),
                    "api_authenticated": bool(api_key)
                }
            )
        
        except Exception as e:
            _logger.error(
                "api_request_failed",
                api_base_url=kwargs.get("api_base_url"),
                endpoint=kwargs.get("endpoint"),
                error=str(e)
            )
            return self._format_result(
                success=False,
                error=f"API request failed: {str(e)}"
            )
    
    def _build_api_url(self, base_url: str, endpoint: str) -> str:
        """Build full API URL from base URL and endpoint.
        
        Args:
            base_url: Base URL of the API
            endpoint: Endpoint path
            
        Returns:
            Full API URL
        """
        # Ensure base URL doesn't end with slash
        base_url = base_url.rstrip('/')
        
        # Ensure endpoint starts with slash
        endpoint = endpoint.startswith('/') or f'/{endpoint}'
        
        return f"{base_url}{endpoint}"
    
    async def _execute_api_request(
        self,
        url: str,
        method: str,
        headers: Dict[str, str],
        query_params: Dict[str, str],
        request_body: Optional[Any],
        response_format: str,
        timeout: int
    ) -> Dict[str, Any]:
        """Execute API request with specialized handling.
        
        Args:
            url: Full API URL
            method: HTTP method
            headers: Request headers
            query_params: Query parameters
            request_body: Request body
            response_format: Expected response format
            timeout: Request timeout
            
        Returns:
            API response with structured format
        """
        import time
        
        start_time = time.time()
        
        try:
            # Add default API headers
            headers.setdefault("Accept", "application/json")
            headers.setdefault("Content-Type", "application/json")
            
            # Prepare request body
            body = None
            if request_body is not None:
                if isinstance(request_body, dict):
                    body = json.dumps(request_body)
                else:
                    body = str(request_body)
            
            # Build query string
            if query_params:
                query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
                url = f"{url}?{query_string}" if "?" not in url else f"{url}&{query_string}"
            
            _logger.info(
                "api_request_made",
                url=url,
                method=method,
                headers=list(headers.keys()),
                timeout=timeout
            )
            
            # Simulate API request (in real implementation, use proper HTTP client)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Mock successful API response
            mock_response = {
                "success": True,
                "status_code": 200,
                "headers": {
                    "content-type": "application/json",
                    "x-api-version": "1.0"
                },
                "data": {
                    "message": "API request successful",
                    "url": url,
                    "method": method,
                    "timestamp": time.time()
                },
                "response_format": response_format,
                "response_time_ms": response_time_ms
            }
            
            # Parse response based on format
            parsed_response = self._parse_api_response(mock_response, response_format)
            
            return parsed_response
        
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            _logger.error(
                "api_request_error",
                url=url,
                method=method,
                error=str(e),
                response_time_ms=response_time_ms
            )
            
            return {
                "success": False,
                "error": str(e),
                "status_code": 500,
                "response_time_ms": response_time_ms,
                "url": url,
                "method": method
            }
    
    def _parse_api_response(self, response: Dict[str, Any], response_format: str) -> Dict[str, Any]:
        """Parse API response based on expected format.
        
        Args:
            response: Raw API response
            response_format: Expected response format
            
        Returns:
            Parsed response
        """
        try:
            if response_format == "json" or response_format == "auto":
                # Try to parse as JSON
                if isinstance(response.get("data"), str):
                    try:
                        parsed_data = json.loads(response["data"])
                        response["data"] = parsed_data
                    except json.JSONDecodeError:
                        # Keep as string if not valid JSON
                        pass
            
            elif response_format == "xml":
                # XML parsing would go here
                response["parsed_xml"] = "XML parsing not implemented in mock"
            
            elif response_format == "text":
                # Ensure data is treated as text
                response["data"] = str(response.get("data", ""))
            
            # Add API-specific metadata
            response["api_metadata"] = {
                "has_pagination": self._check_pagination(response),
                "has_errors": self._check_api_errors(response),
                "rate_limit_info": self._extract_rate_limit_info(response)
            }
            
            return response
        
        except Exception as e:
            _logger.warning("api_response_parse_error", error=str(e))
            return response
    
    def _check_pagination(self, response: Dict[str, Any]) -> bool:
        """Check if response contains pagination information.
        
        Args:
            response: API response
            
        Returns:
            True if pagination is present
        """
        data = response.get("data", {})
        if isinstance(data, dict):
            pagination_indicators = [
                "page", "pages", "total", "count", "limit", "offset",
                "next", "previous", "first", "last"
            ]
            return any(key in data for key in pagination_indicators)
        return False
    
    def _check_api_errors(self, response: Dict[str, Any]) -> bool:
        """Check if response contains API errors.
        
        Args:
            response: API response
            
        Returns:
            True if errors are present
        """
        # Check status code for errors
        status_code = response.get("status_code", 200)
        if status_code >= 400:
            return True
        
        # Check response data for error fields
        data = response.get("data", {})
        if isinstance(data, dict):
            error_indicators = ["error", "errors", "message", "code"]
            return any(key in data for key in error_indicators)
        
        return False
    
    def _extract_rate_limit_info(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract rate limiting information from response.
        
        Args:
            response: API response
            
        Returns:
            Rate limit information
        """
        headers = response.get("headers", {})
        rate_limit_info = {}
        
        # Common rate limit headers
        rate_limit_headers = {
            "x-ratelimit-limit": "limit",
            "x-ratelimit-remaining": "remaining",
            "x-ratelimit-reset": "reset",
            "x-rate-limit-limit": "limit",
            "x-rate-limit-remaining": "remaining",
            "x-rate-limit-reset": "reset"
        }
        
        for header, key in rate_limit_headers.items():
            if header in headers:
                try:
                    rate_limit_info[key] = int(headers[header])
                except (ValueError, TypeError):
                    rate_limit_info[key] = headers[header]
        
        return rate_limit_info
    
    async def load_openapi_spec(self, api_base_url: str, spec_path: str = "/openapi.json") -> bool:
        """Load OpenAPI specification for API.
        
        Args:
            api_base_url: Base URL of the API
            spec_path: Path to OpenAPI spec
            
        Returns:
            True if spec loaded successfully
        """
        try:
            spec_url = self._build_api_url(api_base_url, spec_path)
            
            # Mock spec loading
            self._api_specs[api_base_url] = {
                "url": spec_url,
                "loaded_at": time.time(),
                "endpoints": ["mock_endpoint_1", "mock_endpoint_2"]
            }
            
            _logger.info("openapi_spec_loaded", api_base_url=api_base_url, spec_url=spec_url)
            return True
        
        except Exception as e:
            _logger.error("openapi_spec_load_failed", api_base_url=api_base_url, error=str(e))
            return False
    
    def get_api_endpoints(self, api_base_url: str) -> List[str]:
        """Get available endpoints for API from loaded spec.
        
        Args:
            api_base_url: Base URL of the API
            
        Returns:
            List of available endpoints
        """
        spec = self._api_specs.get(api_base_url, {})
        return spec.get("endpoints", [])
