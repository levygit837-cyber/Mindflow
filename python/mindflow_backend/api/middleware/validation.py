"""Validation middleware for centralized input validation and security."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.sanitizer import SanitizationError, sanitize_message

_logger = get_logger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized validation, sanitization, and security checks."""
    
    def __init__(self, app, max_request_size: int = 10_000_000):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.blocked_patterns = self._init_blocked_patterns()
        self.rate_limit_store: Dict[str, Dict] = {}
    
    def _init_blocked_patterns(self) -> List[str]:
        """Initialize blocked patterns for security."""
        return [
            # SQL injection patterns
            "(?i)union\\s+select",
            "(?i)drop\\s+table", 
            "(?i)insert\\s+into",
            "(?i)delete\\s+from",
            "(?i);\\s*(drop|alter|truncate|exec)",
            # XSS patterns
            "<script[^>]*>.*?</script>",
            "javascript:",
            "on\\w+\\s*=",
            # Path traversal
            "\\.\\.[\\/\\\\]",
            # Command injection
            "\\$\\(",
            "`[^`]*`",
            "\\|\\s*[a-zA-Z]",
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through validation pipeline."""
        is_sse = "text/event-stream" in request.headers.get("accept", "")
        # SSE streaming: bypass ALL middleware processing to prevent BaseHTTPMiddleware
        # from introducing buffering or head-of-line blocking on the response stream.
        if is_sse:
            return await call_next(request)

        try:
            # 1. Size validation
            await self._validate_request_size(request)

            # 2. Rate limiting check
            await self._check_rate_limit(request)

            # 3. Content validation (safe to run even on SSE requests —
            #    validates the *request* body, not the response)
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)

            # 4. Header validation
            self._validate_headers(request)

            # Process request
            response = await call_next(request)

            # 5. Response security headers — skip for SSE to avoid any
            #    interaction with the streaming response object.
            if not is_sse:
                response = self._add_security_headers(response)

            return response
            
        except HTTPException:
            raise
        except Exception as e:
            _logger.error(f"Validation middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Validation failed"}
            )
    
    async def _validate_request_size(self, request: Request) -> None:
        """Validate request size against limits."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Request too large. Max size: {self.max_request_size} bytes"
            )
    
    async def _check_rate_limit(self, request: Request) -> None:
        """Basic rate limiting by client IP."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute window
        self.rate_limit_store = {
            ip: data for ip, data in self.rate_limit_store.items()
            if data.get("last_request", 0) > cutoff_time
        }
        
        # Check current IP
        if client_ip in self.rate_limit_store:
            data = self.rate_limit_store[client_ip]
            if data["count"] >= 100:  # 100 requests per minute
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            data["count"] += 1
            data["last_request"] = current_time
        else:
            self.rate_limit_store[client_ip] = {
                "count": 1,
                "last_request": current_time
            }
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate and sanitize request body."""
        try:
            body = await request.body()
            
            if not body:
                return
            
            # Try to parse as JSON for validation
            try:
                body_data = json.loads(body.decode())
                await self._sanitize_json_data(body_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # For non-JSON content, just check for blocked patterns
                body_text = body.decode(errors="ignore")
                await self._check_blocked_patterns(body_text)
            
        except Exception as e:
            _logger.warning(f"Request body validation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request body"
            )
    
    async def _sanitize_json_data(self, data: Any, path: str = "") -> None:
        """Recursively sanitize JSON data."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    try:
                        data[key] = sanitize_message(value)
                    except SanitizationError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid content in field: {current_path}"
                        )
                elif isinstance(value, (dict, list)):
                    await self._sanitize_json_data(value, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if isinstance(item, str):
                    try:
                        data[i] = sanitize_message(item)
                    except SanitizationError:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid content in field: {current_path}"
                        )
                elif isinstance(item, (dict, list)):
                    await self._sanitize_json_data(item, current_path)
    
    async def _check_blocked_patterns(self, text: str) -> None:
        """Check text against blocked security patterns."""
        import re
        
        for pattern in self.blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                _logger.warning(f"Blocked pattern detected: {pattern[:50]}...")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request contains potentially harmful content"
                )
    
    def _validate_headers(self, request: Request) -> None:
        """Validate request headers for security."""
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "x-originating-ip",
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                # Basic validation for IP headers
                if not self._is_valid_ip_header(value):
                    _logger.warning(f"Suspicious header detected: {header}={value}")
    
    def _is_valid_ip_header(self, value: str) -> bool:
        """Basic validation for IP header values."""
        # Very basic check - can be enhanced
        return len(value) < 100 and not any(char in value for char in "<>'\"")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request."""
        # Try various headers for real IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response."""
        # Note: Some headers may be added by SecurityHeadersMiddleware
        # These are additional headers for validation middleware
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
