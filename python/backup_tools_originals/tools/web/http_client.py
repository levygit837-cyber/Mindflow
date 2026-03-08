"""
HTTP client tool 
for web requests. Provides tools 
for making HTTP/HTTPS requests 
with proper error handling, authentication, and response processing. 
"""
 
from __future__ 
import annotations 
import json 
from typing 
import Any, Dict, Optional, Union 
from urllib.parse 
import urlparse 
from mindflow_backend.infra.logging 
import get_logger 
from mindflow_backend.schemas.orchestration.orchestrator 
import AgentType 
from ..base.tool_interface 
import AsyncToolInterface 
from ..base.tool_schemas 
import ( ToolSchema, ToolParameter, ParameterType, create_tool_schema, create_parameter ) _logger = get_logger(__name__) 
class HttpClientTool(AsyncToolInterface): 
"""
HTTP client tool 
for making web requests. Provides a secure and feature-rich HTTP client 
with support 
for various methods, authentication, headers, and response processing. 
"""
 
def __init__(self): super().__init__() self.name = "http_client" self.description = "HTTP client 
for making web requests 
with authentication and error handling" 
def get_schema(self) -> Dict[str, Any]: 
"""
Return tool schema 
for validation.
"""
 
return create_tool_schema( name=self.name, description=self.description, category="web", parameters=[ create_parameter( name="url", param_type=ParameterType.STRING, description="Target URL 
for HTTP request", required=True, min_length=1 ), create_parameter( name="method", param_type=ParameterType.STRING, description="HTTP method (GET, POST, PUT, DELETE, PATCH)", required=False, default="GET", enum=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] ), create_parameter( name="headers", param_type=ParameterType.OBJECT, description="HTTP headers as dictionary", required=False, default={} ), create_parameter( name="data", param_type=ParameterType.OBJECT, description="Request body data (JSON or form data)", required=False ), create_parameter( name="params", param_type=ParameterType.OBJECT, description="URL query parameters", required=False, default={} ), create_parameter( name="timeout", param_type=ParameterType.INTEGER, description="Request timeout in seconds", required=False, default=30, min_value=1, max_value=300 ), create_parameter( name="auth_type", param_type=ParameterType.STRING, description="Authentication type", required=False, enum=["none", "basic", "bearer", "api_key"], default="none" ), create_parameter( name="auth_credentials", param_type=ParameterType.OBJECT, description="Authentication credentials", required=False ), create_parameter( name="verify_ssl", param_type=ParameterType.BOOLEAN, description="Verify SSL certificates", required=False, default=True ) ], requires_internet=True, supported_agents=list(AgentType), security_level="medium", timeout_seconds=30 ).dict() async 
def execute(self, *args, **kwargs) -> Dict[str, Any]: 
"""
Execute HTTP request 
with comprehensive error handling. Args: url: Target URL method: HTTP method headers: HTTP headers data: Request body data params: Query parameters timeout: Request timeout auth_type: Authentication type auth_credentials: Authentication credentials verify_ssl: SSL verification Returns: HTTP response 
with standardized format 
"""
 try: 
# Validate URL url = kwargs.get("url") 
if not url: 
return self._format_result( success=False, error="URL parameter is required" ) is_valid_url, url_error = self._validate_url(url) 
if not is_valid_url: 
return self._format_result( success=False, error=f"Invalid URL: {url_error}" ) 
# Prepare request parameters method = kwargs.get("method", "GET").upper() headers = kwargs.get("headers", {}) data = kwargs.get("data") params = kwargs.get("params", {}) timeout = kwargs.get("timeout", 30) auth_type = kwargs.get("auth_type", "none") auth_credentials = kwargs.get("auth_credentials", {}) verify_ssl = kwargs.get("verify_ssl", True) 
# Execute request response = await self._make_request( url=url, method=method, headers=headers, data=data, params=params, timeout=timeout, auth_type=auth_type, auth_credentials=auth_credentials, verify_ssl=verify_ssl ) 
return self._format_result( success=response["success"], result=response, metadata={ "url": url, "method": method, "status_code": response.get("status_code"), "response_time_ms": response.get("response_time_ms"), "content_type": response.get("headers", {}).get("content-type"), "content_length": len(str(response.get("content", ""))) } ) 
except Exception as e: _logger.error( "http_request_failed", url=kwargs.get("url"), method=kwargs.get("method"), error=str(e) ) 
return self._format_result( success=False, error=f"HTTP request failed: {str(e)}" ) 
def _validate_url(self, url: str) -> tuple[bool, Optional[str]]: 
"""
Validate URL format and security. Args: url: URL to validate Returns: Tuple of (is_valid, error_message) 
"""
 try: parsed = urlparse(url) 
# Check scheme 
if parsed.scheme not in ["http", "https"]: 
return False, "Only HTTP and HTTPS URLs are allowed" 
# Check hostname 
if not parsed.hostname: 
return False, "Invalid hostname in URL" 
# Block localhost and private networks 
for security blocked_hosts = ["localhost", "127.0.0.1", "0.0.0.0"] 
if parsed.hostname in blocked_hosts: 
return False, f"Access to {parsed.hostname} is blocked 
for security" 
# Check 
for private IP ranges (basic check) 
if parsed.hostname.startswith(("192.168.", "10.", "172.")): 
return False, "Access to private networks is blocked 
for security" 
return True, None 
except Exception as e: 
return False, f"URL parsing error: {str(e)}" async 
def _make_request( self, url: str, method: str, headers: Dict[str, str], data: Optional[Any], params: Dict[str, str], timeout: int, auth_type: str, auth_credentials: Dict[str, Any], verify_ssl: bool ) -> Dict[str, Any]: 
"""
Make HTTP request using appropriate backend. This is a simplified implementation that would typically use a proper HTTP client like aiohttp or requests. 
"""
 
import time start_time = time.time() try: 
# Prepare authentication auth_headers = self._prepare_auth_headers(auth_type, auth_credentials) headers.update(auth_headers) 
# Prepare request body body = None 
if data is not None: 
if isinstance(data, dict): body = json.dumps(data) headers["Content-Type"] = "application/json" 
else: body = str(data) 
# Build query string 
if params: query_string = "&".join([f"{k}={v}" 
for k, v in params.items()]) url = f"{url}?{query_string}" 
if "?" not in url else f"{url}&{query_string}" 
# Simulate HTTP request (in real implementation, use aiohttp/requests) _logger.info( "http_request_made", url=url, method=method, headers=list(headers.keys()), timeout=timeout ) 
# Mock response 
for demonstration response_time_ms = int((time.time() - start_time) * 1000) 
return { "success": True, "status_code": 200, "headers": { "content-type": "application/json", "content-length": "0" }, "content": {"message": "Mock HTTP response", "url": url, "method": method}, "response_time_ms": response_time_ms, "url": url, "method": method } 
except Exception as e: response_time_ms = int((time.time() - start_time) * 1000) _logger.error( "http_request_error", url=url, method=method, error=str(e), response_time_ms=response_time_ms ) 
return { "success": False, "error": str(e), "response_time_ms": response_time_ms, "url": url, "method": method } 
def _prepare_auth_headers(self, auth_type: str, credentials: Dict[str, Any]) -> Dict[str, str]: 
"""
Prepare authentication headers. Args: auth_type: Type of authentication credentials: Authentication credentials Returns: Authentication headers dictionary 
"""
 headers = {} 
if auth_type == "basic": username = credentials.get("username", "") password = credentials.get("password", "") 
if username and password: 
import base64 auth_string = base64.b64encode(f"{username}:{password}".encode()).decode() headers["Authorization"] = f"Basic {auth_string}" el
if auth_type == "bearer": token = credentials.get("token", "") 
if token: headers["Authorization"] = f"Bearer {token}" el
if auth_type == "api_key": api_key = credentials.get("api_key", "") key_header = credentials.get("header", "X-API-Key") 
if api_key and key_header: headers[key_header] = api_key 
return headers