"""HTTP utilities for MindFlow backend.

Generic HTTP client and network-related helpers.
"""

import asyncio
import json
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin, urlparse

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None  # type: ignore[assignment]
    AIOHTTP_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class HTTPClient:
    """Generic HTTP client with retry support."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        default_headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.default_headers = default_headers or {}
        self.timeout = timeout
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base URL and endpoint."""
        if self.base_url:
            return urljoin(self.base_url, endpoint)
        return endpoint
    
    async def get_async(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make async GET request."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for async HTTP requests")
        
        url = self._build_url(endpoint)
        request_headers = {**self.default_headers, **(headers or {})}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                **kwargs
            ) as response:
                return await self._handle_response(response)
    
    async def post_async(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make async POST request."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for async HTTP requests")
        
        url = self._build_url(endpoint)
        request_headers = {**self.default_headers, **(headers or {})}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=data,
                json=json_data,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                **kwargs
            ) as response:
                return await self._handle_response(response)
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make synchronous GET request."""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests is required for sync HTTP requests")
        
        url = self._build_url(endpoint)
        request_headers = {**self.default_headers, **(headers or {})}
        
        response = requests.get(
            url,
            params=params,
            headers=request_headers,
            timeout=self.timeout,
            **kwargs
        )
        return self._handle_sync_response(response)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Make synchronous POST request."""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests is required for sync HTTP requests")
        
        url = self._build_url(endpoint)
        request_headers = {**self.default_headers, **(headers or {})}
        
        response = requests.post(
            url,
            data=data,
            json=json_data,
            headers=request_headers,
            timeout=self.timeout,
            **kwargs
        )
        return self._handle_sync_response(response)
    
    async def _handle_response(self, response: "aiohttp.ClientResponse") -> Dict[str, Any]:
        """Handle async HTTP response."""
        try:
            content = await response.text()
            content_type = response.headers.get('content-type', '').lower()
            
            result = {
                'status_code': response.status,
                'headers': dict(response.headers),
                'url': str(response.url),
            }
            
            if 'application/json' in content_type:
                try:
                    result['data'] = json.loads(content)
                except json.JSONDecodeError:
                    result['data'] = content
            else:
                result['data'] = content
            
            result['success'] = 200 <= response.status < 300
            return result
            
        except Exception as exc:
            _logger.error("http_response_error", error=str(exc))
            raise
    
    def _handle_sync_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle synchronous HTTP response."""
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            result = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'url': response.url,
            }
            
            if 'application/json' in content_type:
                try:
                    result['data'] = response.json()
                except json.JSONDecodeError:
                    result['data'] = response.text
            else:
                result['data'] = response.text
            
            result['success'] = 200 <= response.status_code < 300
            return result
            
        except Exception as exc:
            _logger.error("http_response_error", error=str(exc))
            raise


def parse_response_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """Parse HTTP response headers into structured data."""
    parsed = {}
    
    for key, value in headers.items():
        # Parse common headers
        if key.lower() == 'content-type':
            parsed['content_type'] = {
                'type': value.split(';')[0].strip(),
                'charset': None,
            }
            if 'charset=' in value:
                charset = value.split('charset=')[1].strip()
                parsed['content_type']['charset'] = charset.strip('"')
        
        elif key.lower() == 'content-length':
            try:
                parsed['content_length'] = int(value)
            except ValueError:
                parsed['content_length'] = value
        
        elif key.lower() == 'cache-control':
            # Parse cache control directives
            directives = {}
            for directive in value.split(','):
                if '=' in directive:
                    k, v = directive.split('=', 1)
                    directives[k.strip()] = v.strip()
                else:
                    directives[directive.strip()] = True
            parsed['cache_control'] = directives
        
        else:
            parsed[key.lower().replace('-', '_')] = value
    
    return parsed


def is_success_status(status_code: int) -> bool:
    """Check if HTTP status code indicates success."""
    return 200 <= status_code < 300


def is_client_error(status_code: int) -> bool:
    """Check if HTTP status code indicates client error."""
    return 400 <= status_code < 500


def is_server_error(status_code: int) -> bool:
    """Check if HTTP status code indicates server error."""
    return 500 <= status_code < 600


def get_status_category(status_code: int) -> str:
    """Get category of HTTP status code."""
    if 100 <= status_code < 200:
        return "informational"
    elif 200 <= status_code < 300:
        return "success"
    elif 300 <= status_code < 400:
        return "redirection"
    elif 400 <= status_code < 500:
        return "client_error"
    elif 500 <= status_code < 600:
        return "server_error"
    else:
        return "unknown"


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def extract_path(url: str) -> Optional[str]:
    """Extract path from URL."""
    try:
        parsed = urlparse(url)
        return parsed.path
    except Exception:
        return None


def build_query_string(params: Dict[str, Any]) -> str:
    """Build query string from parameters."""
    from urllib.parse import urlencode
    
    # Convert non-string values to strings
    string_params = {}
    for key, value in params.items():
        if value is not None:
            string_params[key] = str(value)
    
    return urlencode(string_params)


async def download_file_async(url: str, output_path: str) -> Dict[str, Any]:
    """Download file asynchronously."""
    if not AIOHTTP_AVAILABLE:
        raise ImportError("aiohttp is required for async file download")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                # Get file size
                content_length = response.headers.get('content-length')
                total_size = int(content_length) if content_length else None
                
                # Download file
                downloaded_size = 0
                with open(output_path, 'wb') as file:
                    async for chunk in response.content.iter_chunked(8192):
                        file.write(chunk)
                        downloaded_size += len(chunk)
                
                return {
                    'success': True,
                    'output_path': output_path,
                    'downloaded_size': downloaded_size,
                    'total_size': total_size,
                    'url': url,
                }
    
    except Exception as exc:
        _logger.error("file_download_error", url=url, error=str(exc))
        return {
            'success': False,
            'error': str(exc),
            'url': url,
        }


def create_user_agent(name: str, version: str = "1.0.0") -> str:
    """Create user agent string."""
    import platform
    import sys
    
    system_info = f"{platform.system()} {platform.release()}"
    python_info = f"Python/{sys.version.split()[0]}"
    
    return f"{name}/{version} ({system_info}) {python_info}"
