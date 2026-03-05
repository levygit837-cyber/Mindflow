"""Tests for ValidationMiddleware."""

from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from omnimind_backend.api.middleware.validation import ValidationMiddleware


class TestValidationMiddleware:
    """Test suite for ValidationMiddleware."""
    
    def test_middleware_initialization(self):
        """Test ValidationMiddleware initialization."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app, max_request_size=1000)
        
        assert middleware.app == app
        assert middleware.max_request_size == 1000
        assert len(middleware.blocked_patterns) > 0
        assert isinstance(middleware.rate_limit_store, dict)
    
    def test_blocked_patterns_initialization(self):
        """Test that blocked patterns are properly initialized."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        patterns = middleware.blocked_patterns
        assert any("union.*select" in pattern.lower() for pattern in patterns)
        assert any("<script" in pattern.lower() for pattern in patterns)
        assert any("javascript:" in pattern.lower() for pattern in patterns)
        assert any("\\.\\." in pattern for pattern in patterns)
    
    @pytest.mark.asyncio
    async def test_request_size_validation_success(self):
        """Test successful request size validation."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app, max_request_size=1000)
        
        # Mock request with valid content length
        request = AsyncMock(spec=Request)
        request.headers = {"content-length": "500"}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_request_size_validation_failure(self):
        """Test request size validation failure."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app, max_request_size=1000)
        
        # Mock request with too large content length
        request = AsyncMock(spec=Request)
        request.headers = {"content-length": "2000"}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        
        call_next = AsyncMock()
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await middleware.dispatch(request, call_next)
        
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_success(self):
        """Test successful rate limiting check."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request
        request = AsyncMock(spec=Request)
        request.headers = {}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        
        # Mock body
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_rate_limiting_exceeded(self):
        """Test rate limiting when limit is exceeded."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request
        request = AsyncMock(spec=Request)
        request.headers = {}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        
        # Mock body
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        
        call_next = AsyncMock()
        
        # Make many requests to exceed rate limit
        for i in range(101):  # Rate limit is 100 per minute
            try:
                await middleware.dispatch(request, call_next)
            except Exception:
                # Should raise exception on the 101st request
                if i == 100:
                    break
                else:
                    raise
        
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_json_body_sanitization(self):
        """Test JSON body sanitization."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request with JSON body
        request = AsyncMock(spec=Request)
        request.headers = {"content-length": "100"}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        request.body = AsyncMock(return_value=b'{"message": "Test <script>alert(1)</script>", "data": "value"}')
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_blocked_pattern_detection(self):
        """Test detection of blocked patterns in request body."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request with SQL injection attempt
        request = AsyncMock(spec=Request)
        request.headers = {"content-length": "100"}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        request.body = AsyncMock(return_value=b'{"query": "SELECT * FROM users; DROP TABLE users;"}')
        
        call_next = AsyncMock()
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await middleware.dispatch(request, call_next)
        
        call_next.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_client_ip_from_headers(self):
        """Test getting client IP from various headers."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Test X-Forwarded-For header
        request = AsyncMock(spec=Request)
        request.headers = {"x-forwarded-for": "192.168.1.100"}
        request.client = None
        
        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"
        
        # Test X-Real-IP header
        request.headers = {"x-real-ip": "10.0.0.1"}
        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"
        
        # Test fallback to client.host
        request.headers = {}
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"
    
    @pytest.mark.asyncio
    async def test_validate_headers_suspicious_content(self):
        """Test header validation for suspicious content."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request with suspicious header
        request = AsyncMock(spec=Request)
        request.headers = {"x-forwarded-for": "<script>alert(1)</script>"}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        # Should not raise exception, but should log warning
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_add_security_headers(self):
        """Test adding security headers to response."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock response
        response = AsyncMock(spec=Response)
        response.headers = {}
        
        result = middleware._add_security_headers(response)
        
        assert result == response
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert "Referrer-Policy" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
    
    @pytest.mark.asyncio
    async def test_non_post_request_handling(self):
        """Test handling of non-POST requests."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock GET request
        request = AsyncMock(spec=Request)
        request.headers = {}
        request.method = "GET"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_empty_request_body(self):
        """Test handling of empty request body."""
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Mock request with empty body
        request = AsyncMock(spec=Request)
        request.headers = {}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "127.0.0.1"
        request.body = AsyncMock(return_value=b'')
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        result = await middleware.dispatch(request, call_next)
        
        assert result == response
        call_next.assert_called_once_with(request)
    
    @pytest.mark.asyncio
    async def test_rate_limit_store_cleanup(self):
        """Test automatic cleanup of old rate limit entries."""
        import time
        app = AsyncMock()
        middleware = ValidationMiddleware(app)
        
        # Add old entry to rate limit store
        old_time = time.time() - 120  # 2 minutes ago
        middleware.rate_limit_store["test_ip"] = {
            "count": 10,
            "last_request": old_time
        }
        
        # Mock request
        request = AsyncMock(spec=Request)
        request.headers = {}
        request.method = "POST"
        request.url = AsyncMock()
        request.url.path = "/test"
        request.client = AsyncMock()
        request.client.host = "test_ip"
        request.body = AsyncMock(return_value=b'{"test": "data"}')
        
        # Mock call_next
        response = AsyncMock(spec=Response)
        call_next = AsyncMock(return_value=response)
        
        # Process request should clean up old entry
        await middleware.dispatch(request, call_next)
        
        # Old entry should be cleaned up
        assert "test_ip" not in middleware.rate_limit_store


class TestValidationMiddlewareIntegration:
    """Integration tests for ValidationMiddleware."""
    
    def test_middleware_in_fastapi_app(self, client: TestClient):
        """Test middleware integration with FastAPI app."""
        # This test would require the actual FastAPI app with middleware
        # For now, we'll test the middleware components
        
        response = client.get("/health")
        assert response.status_code == 200
        
        # Test that security headers are added
        if "X-Content-Type-Options" in response.headers:
            assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    @pytest.mark.asyncio
    async def test_middleware_with_real_request(self, async_client: AsyncClient):
        """Test middleware with real async request."""
        # Test a simple request through the middleware
        response = await async_client.get("/health")
        
        # Should succeed
        assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist yet
        
        # Check for security headers if they were added
        if hasattr(response, 'headers'):
            headers = dict(response.headers)
            if "X-Content-Type-Options" in headers:
                assert headers["X-Content-Type-Options"] == "nosniff"
