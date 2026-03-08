"""Advanced middleware pipeline system.

Provides comprehensive middleware processing with
ordering, error handling, and performance monitoring.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union, AsyncGenerator
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import uuid
import weakref

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.tracer import get_tracer, SpanKind
from mindflow_backend.infra.api.gateway import RequestInfo, ResponseInfo

_logger = get_logger(__name__)


class MiddlewareType(Enum):
    """Middleware types."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMITING = "rate_limiting"
    LOGGING = "logging"
    METRICS = "metrics"
    TRACING = "tracing"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ERROR_HANDLING = "error_handling"
    CUSTOM = "custom"


class MiddlewareOrder(Enum):
    """Middleware execution order."""
    BEFORE = "before"
    AFTER = "after"
    AROUND = "around"
    ERROR = "error"


@dataclass
class MiddlewareContext:
    """Middleware execution context."""
    request_id: str
    request_info: RequestInfo
    response_info: Optional[ResponseInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: Optional[datetime] = None
    execution_time_ms: float = 0.0
    error: Optional[Exception] = None
    completed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "request_info": self.request_info.to_dict(),
            "response_info": self.response_info.to_dict() if self.response_info else None,
            "metadata": self.metadata,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_ms": self.execution_time_ms,
            "error": str(self.error) if self.error else None,
            "completed": self.completed,
        }


class Middleware(ABC):
    """Abstract middleware base class."""
    
    def __init__(self, name: str, middleware_type: MiddlewareType, priority: int = 0):
        """Initialize middleware.
        
        Args:
            name: Middleware name
            middleware_type: Middleware type
            priority: Execution priority (higher = earlier)
        """
        self.name = name
        self.type = middleware_type
        self.priority = priority
        self.enabled = True
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_execution_time_ms = 0.0
        self.avg_execution_time_ms = 0.0
        
    @abstractmethod
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process incoming request.
        
        Args:
            context: Middleware context
            
        Returns:
            Updated context
        """
        pass
        
    async def process_response(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process outgoing response.
        
        Args:
            context: Middleware context
            
        Returns:
            Updated context
        """
        return context
        
    async def handle_error(self, context: MiddlewareContext, error: Exception) -> MiddlewareContext:
        """Handle processing error.
        
        Args:
            context: Middleware context
            error: Processing error
            
        Returns:
            Updated context
        """
        context.error = error
        return context
        
    def update_metrics(self, execution_time_ms: float, success: bool) -> None:
        """Update middleware metrics.
        
        Args:
            execution_time_ms: Execution time in milliseconds
            success: Processing was successful
        """
        self.execution_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        # Update average execution time
        if self.execution_count == 1:
            self.avg_execution_time_ms = execution_time_ms
        else:
            self.avg_execution_time_ms = (
                (self.avg_execution_time_ms * (self.execution_count - 1) + execution_time_ms) / self.execution_count
            )
            
        self.total_execution_time_ms += execution_time_ms
        
    def get_success_rate(self) -> float:
        """Get success rate.
        
        Returns:
            Success rate (0.0-1.0)
        """
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_execution_time_ms": self.total_execution_time_ms,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "success_rate": self.get_success_rate(),
        }


class AuthenticationMiddleware(Middleware):
    """Authentication middleware."""
    
    def __init__(self, name: str = "authentication"):
        """Initialize authentication middleware."""
        super().__init__(name, MiddlewareType.AUTHENTICATION, priority=100)
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process authentication."""
        start_time = time.time()
        
        try:
            # Extract authentication token
            auth_header = context.request_info.headers.get("Authorization", "")
            api_key = context.request_info.headers.get("X-API-Key", "")
            
            # Validate authentication
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                # Validate JWT token (simplified)
                context.metadata["auth_method"] = "jwt"
                context.metadata["auth_token"] = token
                context.metadata["authenticated"] = True
            elif api_key:
                # Validate API key (simplified)
                context.metadata["auth_method"] = "api_key"
                context.metadata["api_key"] = api_key
                context.metadata["authenticated"] = True
            else:
                context.metadata["authenticated"] = False
                
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise
            
    async def handle_error(self, context: MiddlewareContext, error: Exception) -> MiddlewareContext:
        """Handle authentication error."""
        context.metadata["auth_error"] = str(error)
        context.metadata["authenticated"] = False
        return await super().handle_error(context, error)


class AuthorizationMiddleware(Middleware):
    """Authorization middleware."""
    
    def __init__(self, name: str = "authorization"):
        """Initialize authorization middleware."""
        super().__init__(name, MiddlewareType.AUTHORIZATION, priority=90)
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process authorization."""
        start_time = time.time()
        
        try:
            # Check if user is authenticated
            if not context.metadata.get("authenticated", False):
                raise PermissionError("User not authenticated")
                
            # Check permissions (simplified)
            user_permissions = context.metadata.get("permissions", [])
            required_permissions = self._get_required_permissions(context.request_info)
            
            if not any(perm in user_permissions for perm in required_permissions):
                raise PermissionError("Insufficient permissions")
                
            context.metadata["authorized"] = True
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise
            
    def _get_required_permissions(self, request_info: RequestInfo) -> List[str]:
        """Get required permissions for request.
        
        Args:
            request_info: Request information
            
        Returns:
            List of required permissions
        """
        # Simplified permission mapping
        if request_info.method in ["GET", "HEAD"]:
            return ["read"]
        elif request_info.method in ["POST", "PUT", "PATCH"]:
            return ["write"]
        elif request_info.method == "DELETE":
            return ["delete"]
        else:
            return []
            
    async def handle_error(self, context: MiddlewareContext, error: Exception) -> MiddlewareContext:
        """Handle authorization error."""
        context.metadata["auth_error"] = str(error)
        context.metadata["authorized"] = False
        return await super().handle_error(context, error)


class RateLimitingMiddleware(Middleware):
    """Rate limiting middleware."""
    
    def __init__(self, name: str = "rate_limiting"):
        """Initialize rate limiting middleware."""
        super().__init__(name, MiddlewareType.RATE_LIMITING, priority=80)
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        
    def set_rate_limit(self, key: str, requests_per_minute: int, burst_size: int = 10) -> None:
        """Set rate limit for key.
        
        Args:
            key: Rate limit key
            requests_per_minute: Requests per minute
            burst_size: Burst size
        """
        self._rate_limits[key] = {
            "requests_per_minute": requests_per_minute,
            "burst_size": burst_size,
            "requests": [],
        }
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process rate limiting."""
        start_time = time.time()
        
        try:
            # Get rate limit key (user ID or IP)
            rate_limit_key = context.metadata.get("user_id", context.request_info.client_ip)
            
            # Check rate limit
            if rate_limit_key in self._rate_limits:
                rate_limit = self._rate_limits[rate_limit_key]
                now = time.time()
                
                # Clean old requests
                rate_limit["requests"] = [
                    req_time for req_time in rate_limit["requests"]
                    if now - req_time < 60  # Keep last minute
                ]
                
                # Check if rate limit exceeded
                if len(rate_limit["requests"]) >= rate_limit["requests_per_minute"]:
                    raise Exception("Rate limit exceeded")
                    
                # Add current request
                rate_limit["requests"].append(now)
                
            context.metadata["rate_limited"] = False
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            context.metadata["rate_limited"] = True
            context.metadata["rate_limit_error"] = str(e)
            raise
            
    async def handle_error(self, context: MiddlewareContext, error: Exception) -> MiddlewareContext:
        """Handle rate limiting error."""
        return await super().handle_error(context, error)


class LoggingMiddleware(Middleware):
    """Logging middleware."""
    
    def __init__(self, name: str = "logging"):
        """Initialize logging middleware."""
        super().__init__(name, MiddlewareType.LOGGING, priority=10)
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Log incoming request."""
        start_time = time.time()
        
        try:
            _logger.info(
                "request_started",
                request_id=context.request_id,
                method=context.request_info.method,
                path=context.request_info.path,
                client_ip=context.request_info.client_ip,
                user_agent=context.request_info.user_agent,
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise
            
    async def process_response(self, context: MiddlewareContext) -> MiddlewareContext:
        """Log outgoing response."""
        start_time = time.time()
        
        try:
            if context.response_info:
                _logger.info(
                    "request_completed",
                    request_id=context.request_id,
                    status_code=context.response_info.status_code,
                    duration_ms=context.response_info.duration_ms,
                    error=context.response_info.error,
                )
                
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise


class MetricsMiddleware(Middleware):
    """Metrics collection middleware."""
    
    def __init__(self, name: str = "metrics"):
        """Initialize metrics middleware."""
        super().__init__(name, MiddlewareType.METRICS, priority=5)
        self._metrics: Dict[str, Any] = {}
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Collect request metrics."""
        start_time = time.time()
        
        try:
            # Record request start
            self._metrics[context.request_id] = {
                "start_time": start_time,
                "method": context.request_info.method,
                "path": context.request_info.path,
            }
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise
            
    async def process_response(self, context: MiddlewareContext) -> MiddlewareContext:
        """Collect response metrics."""
        start_time = time.time()
        
        try:
            if context.request_id in self._metrics:
                metrics = self._metrics[context.request_id]
                metrics["end_time"] = time.time()
                metrics["duration_ms"] = (metrics["end_time"] - metrics["start_time"]) * 1000
                
                if context.response_info:
                    metrics["status_code"] = context.response_info.status_code
                    metrics["error"] = context.response_info.error
                    
                # Store metrics (simplified)
                _logger.debug(
                    "metrics_collected",
                    request_id=context.request_id,
                    **metrics
                )
                
                # Clean up
                del self._metrics[context.request_id]
                
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise


class TracingMiddleware(Middleware):
    """Distributed tracing middleware."""
    
    def __init__(self, name: str = "tracing"):
        """Initialize tracing middleware."""
        super().__init__(name, MiddlewareType.TRACING, priority=95)
        self._tracer = get_tracer()
        
    async def process_request(self, context: MiddlewareContext) -> MiddlewareContext:
        """Start request tracing."""
        start_time = time.time()
        
        try:
            # Extract trace context from headers
            trace_context = self._tracer.extract_context_from_headers(context.request_info.headers)
            
            # Start span
            span_name = f"{context.request_info.method} {context.request_info.path}"
            # In a real implementation, you'd use the tracer's span context
            context.metadata["trace_context"] = trace_context
            context.metadata["span_name"] = span_name
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise
            
    async def process_response(self, context: MiddlewareContext) -> MiddlewareContext:
        """End request tracing."""
        start_time = time.time()
        
        try:
            # End span (simplified)
            if context.metadata.get("trace_context"):
                context.metadata["trace_completed"] = True
                
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise


class ErrorHandlingMiddleware(Middleware):
    """Error handling middleware."""
    
    def __init__(self, name: str = "error_handling"):
        """Initialize error handling middleware."""
        super().__init__(name, MiddlewareType.ERROR_HANDLING, priority=1)
        self._error_handlers: Dict[type, Callable] = {}
        
    def register_error_handler(self, error_type: type, handler: Callable) -> None:
        """Register error handler.
        
        Args:
            error_type: Error type to handle
            handler: Error handler function
        """
        self._error_handlers[error_type] = handler
        
    async def handle_error(self, context: MiddlewareContext, error: Exception) -> MiddlewareContext:
        """Handle processing error."""
        start_time = time.time()
        
        try:
            # Log error
            _logger.error(
                "middleware_error",
                request_id=context.request_id,
                error_type=type(error).__name__,
                error_message=str(error),
                middleware=context.metadata.get("current_middleware", "unknown"),
            )
            
            # Try to handle error with registered handler
            error_type = type(error)
            if error_type in self._error_handlers:
                handler = self._error_handlers[error_type]
                try:
                    result = handler(context, error)
                    if asyncio.iscoroutine(result):
                        context = await result
                    else:
                        context = result
                except Exception as handler_error:
                    _logger.error(
                        "error_handler_failed",
                        error_type=error_type.__name__,
                        handler_error=str(handler_error),
                    )
                    
            # Set error information
            context.error = error
            context.metadata["error_handled"] = True
            context.metadata["error_type"] = error_type.__name__
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, True)
            
            return context
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.update_metrics(execution_time_ms, False)
            raise


class MiddlewarePipeline:
    """Advanced middleware pipeline system.
    
    Features:
    - Ordered middleware execution
    - Error handling and recovery
    - Performance monitoring
    - Dynamic middleware management
    - Request/response processing
    """
    
    def __init__(self):
        """Initialize middleware pipeline."""
        self._middlewares: List[Middleware] = []
        self._before_middleware: List[Middleware] = []
        self._after_middleware: List[Middleware] = []
        self._error_middleware: List[Middleware] = []
        self._is_initialized = False
        
        # Pipeline configuration
        self._enable_parallel_processing = False
        self._max_parallel_middleware = 5
        self._timeout_ms = 30000
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_pipeline_time_ms": 0.0,
            "middleware_usage": {},
            "error_count": 0,
        }
        
    async def initialize(self) -> None:
        """Initialize middleware pipeline."""
        # Add default middleware
        await self._setup_default_middleware()
        
        # Organize middleware by order
        self._organize_middleware()
        
        self._is_initialized = True
        
        _logger.info(
            "middleware_pipeline_initialized",
            total_middleware=len(self._middlewares),
            before_middleware=len(self._before_middleware),
            after_middleware=len(self._after_middleware),
            error_middleware=len(self._error_middleware),
        )
        
    def _setup_default_middleware(self) -> None:
        """Setup default middleware."""
        # Add default middleware in order
        self.add_middleware(TracingMiddleware())
        self.add_middleware(LoggingMiddleware())
        self.add_middleware(AuthenticationMiddleware())
        self.add_middleware(AuthorizationMiddleware())
        self.add_middleware(RateLimitingMiddleware())
        self.add_middleware(MetricsMiddleware())
        self.add_middleware(ErrorHandlingMiddleware())
        
    def _organize_middleware(self) -> None:
        """Organize middleware by execution order."""
        self._before_middleware = []
        self._after_middleware = []
        self._error_middleware = []
        
        # Sort by priority
        sorted_middleware = sorted(self._middlewares, key=lambda m: m.priority, reverse=True)
        
        for middleware in sorted_middleware:
            if middleware.type == MiddlewareType.ERROR_HANDLING:
                self._error_middleware.append(middleware)
            else:
                self._before_middleware.append(middleware)
                self._after_middleware.append(middleware)  # Process in reverse order for response
                
        self._after_middleware.reverse()
        
    def add_middleware(self, middleware: Middleware) -> None:
        """Add middleware to pipeline.
        
        Args:
            middleware: Middleware to add
        """
        self._middlewares.append(middleware)
        
        # Reorganize if already initialized
        if self._is_initialized:
            self._organize_middleware()
            
        _logger.debug("middleware_added", name=middleware.name, type=middleware.type.value)
        
    def remove_middleware(self, name: str) -> bool:
        """Remove middleware from pipeline.
        
        Args:
            name: Middleware name
            
        Returns:
            True if middleware was removed
        """
        for i, middleware in enumerate(self._middlewares):
            if middleware.name == name:
                del self._middlewares[i]
                
                # Reorganize if already initialized
                if self._is_initialized:
                    self._organize_middleware()
                    
                _logger.debug("middleware_removed", name=name)
                return True
                
        return False
        
    def get_middleware_by_name(self, name: str) -> Optional[Middleware]:
        """Get middleware by name.
        
        Args:
            name: Middleware name
            
        Returns:
            Middleware or None
        """
        for middleware in self._middlewares:
            if middleware.name == name:
                return middleware
        return None
        
    async def process_request(self, request_info: RequestInfo) -> MiddlewareContext:
        """Process request through pipeline.
        
        Args:
            request_info: Request information
            
        Returns:
            Processing context
        """
        if not self._is_initialized:
            raise RuntimeError("Middleware pipeline not initialized")
            
        start_time = time.time()
        
        # Create context
        context = MiddlewareContext(
            request_id=str(uuid.uuid4()),
            request_info=request_info,
        )
        
        try:
            # Update statistics
            self._stats["total_requests"] += 1
            
            # Process through before middleware
            for middleware in self._before_middleware:
                if not middleware.enabled:
                    continue
                    
                try:
                    context = await middleware.process_request(context)
                    context.metadata["current_middleware"] = middleware.name
                except Exception as e:
                    context = await self._handle_middleware_error(context, middleware, e)
                    if context.error:
                        raise
                        
            # Update pipeline time
            pipeline_time_ms = (time.time() - start_time) * 1000
            context.execution_time_ms = pipeline_time_ms
            
            # Update statistics
            current_avg = self._stats["avg_pipeline_time_ms"]
            count = self._stats["total_requests"]
            self._stats["avg_pipeline_time_ms"] = (current_avg * (count - 1) + pipeline_time_ms) / count
            
            # Update middleware usage
            for middleware in self._before_middleware:
                if middleware.enabled:
                    self._stats["middleware_usage"][middleware.name] = self._stats["middleware_usage"].get(middleware.name, 0) + 1
                    
            _logger.debug(
                "request_processed",
                request_id=context.request_id,
                pipeline_time_ms=pipeline_time_ms,
                middleware_count=len(self._before_middleware),
            )
            
            return context
            
        except Exception as e:
            self._stats["failed_requests"] += 1
            self._stats["error_count"] += 1
            context.error = e
            context.execution_time_ms = (time.time() - start_time) * 1000
            raise
            
    async def process_response(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process response through pipeline.
        
        Args:
            context: Processing context
            
        Returns:
            Updated context
        """
        start_time = time.time()
        
        try:
            # Process through after middleware (reverse order)
            for middleware in self._after_middleware:
                if not middleware.enabled:
                    continue
                    
                try:
                    context = await middleware.process_response(context)
                    context.metadata["current_middleware"] = middleware.name
                except Exception as e:
                    context = await self._handle_middleware_error(context, middleware, e)
                    # Continue processing even if middleware fails
                    
            # Update completion time
            context.end_time = datetime.now(UTC)
            context.completed = True
            
            _logger.debug(
                "response_processed",
                request_id=context.request_id,
                middleware_count=len(self._after_middleware),
            )
            
            return context
            
        except Exception as e:
            _logger.error("response_processing_failed", request_id=context.request_id, error=str(e))
            raise
            
    async def _handle_middleware_error(self, context: MiddlewareContext, middleware: Middleware, error: Exception) -> MiddlewareContext:
        """Handle middleware error.
        
        Args:
            context: Processing context
            middleware: Middleware that failed
            error: Processing error
            
        Returns:
            Updated context
        """
        # Try error middleware first
        for error_middleware in self._error_middleware:
            if error_middleware.enabled:
                try:
                    context = await error_middleware.handle_error(context, error)
                    if not context.error:  # Error was handled
                        break
                except Exception as handler_error:
                    _logger.error(
                        "error_middleware_failed",
                        middleware=error_middleware.name,
                        error=str(handler_error),
                    )
                    
        return context
        
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Calculate success rate
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            
        # Add middleware statistics
        middleware_stats = []
        for middleware in self._middlewares:
            middleware_stats.append(middleware.to_dict())
            
        stats["middleware_stats"] = middleware_stats
        stats["middleware_count"] = len(self._middlewares)
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform pipeline health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test pipeline processing
            test_request = RequestInfo(
                request_id=str(uuid.uuid4()),
                method="GET",
                path="/health",
                headers={},
                query_params={},
                client_ip="127.0.0.1",
            )
            
            try:
                context = await self.process_request(test_request)
                pipeline_healthy = True
            except Exception:
                pipeline_healthy = False
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "pipeline_healthy": pipeline_healthy,
                "middleware_count": len(self._middlewares),
                "enabled_middleware": sum(1 for m in self._middlewares if m.enabled),
                "test_request_processed": pipeline_healthy,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("middleware_pipeline_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("middleware_pipeline_health_check_failed", **error_data)
            return error_data


# Global middleware pipeline instance
_middleware_pipeline: Optional[MiddlewarePipeline] = None


def get_middleware_pipeline() -> MiddlewarePipeline:
    """Get global middleware pipeline instance.
    
    Returns:
        MiddlewarePipeline instance
    """
    global _middleware_pipeline
    if _middleware_pipeline is None:
        _middleware_pipeline = MiddlewarePipeline()
    return _middleware_pipeline
