"""Advanced API Gateway with comprehensive request management.

Provides request routing, load balancing, middleware pipeline,
and advanced API management capabilities.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Callable, AsyncGenerator
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import uuid
import weakref

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.tracer import get_tracer, SpanKind
from mindflow_backend.infra.security.rate_limiter import get_rate_limiter
from mindflow_backend.infra.config import get_settings

_logger = get_logger(__name__)


class GatewayStatus(Enum):
    """API Gateway status."""
    ACTIVE = "active"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


@dataclass
class RequestInfo:
    """Request information for processing."""
    request_id: str
    method: str
    path: str
    headers: Dict[str, str]
    query_params: Dict[str, str]
    body: Optional[bytes] = None
    client_ip: str = "unknown"
    user_agent: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "query_params": self.query_params,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ResponseInfo:
    """Response information."""
    status_code: int
    headers: Dict[str, str]
    body: Optional[bytes] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class RouteConfig:
    """Route configuration."""
    path: str
    method: str
    target_service: str
    target_endpoint: str
    timeout_ms: int = 30000
    retry_attempts: int = 3
    load_balancer: str = "round_robin"
    middleware: List[str] = field(default_factory=list)
    rate_limit_config: Optional[str] = None
    auth_required: bool = True
    cache_ttl: Optional[int] = None
    health_check_path: str = "/health"
    circuit_breaker_threshold: float = 0.5
    enabled: bool = True


@dataclass
class ServiceConfig:
    """Service configuration."""
    name: str
    endpoints: List[str]
    load_balancer: str = "round_robin"
    health_check_interval: int = 30
    health_check_timeout: int = 5000
    circuit_breaker_threshold: float = 0.5
    circuit_breaker_timeout: int = 60
    retry_attempts: int = 3
    timeout_ms: int = 30000
    enabled: bool = True


class LoadBalancer(ABC):
    """Abstract load balancer."""
    
    @abstractmethod
    def select_endpoint(self, endpoints: List[str]) -> str:
        """Select endpoint for request."""
        pass
        
    @abstractmethod
    def report_health(self, endpoint: str, healthy: bool) -> None:
        """Report endpoint health status."""
        pass


class RoundRobinLoadBalancer(LoadBalancer):
    """Round-robin load balancer."""
    
    def __init__(self):
        """Initialize round-robin load balancer."""
        self._current_index = 0
        self._healthy_endpoints: Dict[str, bool] = {}
        
    def select_endpoint(self, endpoints: List[str]) -> str:
        """Select next endpoint in round-robin fashion."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in endpoints 
            if self._healthy_endpoints.get(ep, True)
        ]
        
        if not healthy_endpoints:
            # Fallback to all endpoints if none are healthy
            healthy_endpoints = endpoints
            
        # Select endpoint
        endpoint = healthy_endpoints[self._current_index % len(healthy_endpoints)]
        self._current_index += 1
        
        return endpoint
        
    def report_health(self, endpoint: str, healthy: bool) -> None:
        """Report endpoint health."""
        self._healthy_endpoints[endpoint] = healthy


class WeightedLoadBalancer(LoadBalancer):
    """Weighted load balancer."""
    
    def __init__(self):
        """Initialize weighted load balancer."""
        self._weights: Dict[str, float] = {}
        self._healthy_endpoints: Dict[str, bool] = {}
        
    def set_weight(self, endpoint: str, weight: float) -> None:
        """Set endpoint weight."""
        self._weights[endpoint] = weight
        
    def select_endpoint(self, endpoints: List[str]) -> str:
        """Select endpoint based on weights."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Filter healthy endpoints
        healthy_endpoints = [
            ep for ep in endpoints 
            if self._healthy_endpoints.get(ep, True)
        ]
        
        if not healthy_endpoints:
            # Fallback to all endpoints if none are healthy
            healthy_endpoints = endpoints
            
        # Calculate weighted selection
        total_weight = sum(self._weights.get(ep, 1.0) for ep in healthy_endpoints)
        if total_weight == 0:
            # Fallback to first endpoint
            return healthy_endpoints[0]
            
        import random
        rand = random.uniform(0, total_weight)
        current_weight = 0.0
        
        for endpoint in healthy_endpoints:
            current_weight += self._weights.get(endpoint, 1.0)
            if rand <= current_weight:
                return endpoint
                
        # Fallback to last endpoint
        return healthy_endpoints[-1]
        
    def report_health(self, endpoint: str, healthy: bool) -> None:
        """Report endpoint health."""
        self._healthy_endpoints[endpoint] = healthy


class CircuitBreaker:
    """Circuit breaker for endpoint protection."""
    
    def __init__(self, threshold: float = 0.5, timeout: int = 60):
        """Initialize circuit breaker.
        
        Args:
            threshold: Failure threshold (0.0-1.0)
            timeout: Recovery timeout in seconds
        """
        self.threshold = threshold
        self.timeout = timeout
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    async def call(self, endpoint: str, operation: Callable) -> Any:
        """Execute operation with circuit breaker protection.
        
        Args:
            endpoint: Endpoint identifier
            operation: Operation to execute
            
        Returns:
            Operation result
        """
        current_time = time.time()
        
        # Check if circuit should be half-open
        if (self._state == "OPEN" and 
            self._last_failure_time and 
            current_time - self._last_failure_time > self.timeout):
            self._state = "HALF_OPEN"
            _logger.info("circuit_breaker_half_open", endpoint=endpoint)
            
        # Reject calls if circuit is open
        if self._state == "OPEN":
            raise Exception(f"Circuit breaker OPEN for endpoint: {endpoint}")
            
        try:
            result = await operation()
            
            # Record success
            self._success_count += 1
            
            # Close circuit if we were half-open
            if self._state == "HALF_OPEN":
                self._state = "CLOSED"
                self._failure_count = 0
                self._success_count = 0
                _logger.info("circuit_breaker_closed", endpoint=endpoint)
                
            return result
            
        except Exception as e:
            # Record failure
            self._failure_count += 1
            self._last_failure_time = current_time
            
            # Calculate failure rate
            total_requests = self._failure_count + self._success_count
            failure_rate = self._failure_count / max(total_requests, 1)
            
            # Open circuit if threshold exceeded
            if failure_rate >= self.threshold:
                self._state = "OPEN"
                _logger.warning(
                    "circuit_breaker_opened",
                    endpoint=endpoint,
                    failure_rate=failure_rate,
                    threshold=self.threshold,
                )
                
            raise e
            
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state.
        
        Returns:
            State information
        """
        total_requests = self._failure_count + self._success_count
        failure_rate = self._failure_count / max(total_requests, 1)
        
        return {
            "state": self._state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_rate": failure_rate,
            "threshold": self.threshold,
            "last_failure_time": self._last_failure_time,
        }


class APIGateway:
    """Advanced API Gateway with comprehensive features.
    
    Features:
    - Request routing and load balancing
    - Circuit breaker protection
    - Rate limiting integration
    - Distributed tracing
    - Health checking
    - Middleware pipeline
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize API Gateway."""
        self._routes: Dict[str, RouteConfig] = {}
        self._services: Dict[str, ServiceConfig] = {}
        self._load_balancers: Dict[str, LoadBalancer] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._middleware_pipeline: Optional[Any] = None
        self._tracer = get_tracer()
        self._rate_limiter = get_rate_limiter()
        self._status = GatewayStatus.ACTIVE
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time_ms": 0.0,
            "requests_per_second": 0.0,
            "circuit_breaker_trips": 0,
            "rate_limit_blocks": 0,
            "route_usage": {},
            "service_usage": {},
        }
        
    async def initialize(self) -> None:
        """Initialize API Gateway."""
        await self._tracer.initialize()
        await self._rate_limiter.initialize()
        
        # Initialize default rate limiting configs
        self._rate_limiter.add_config("default", self._create_default_rate_limit())
        
        _logger.info(
            "api_gateway_initialized",
            routes_count=len(self._routes),
            services_count=len(self._services),
            status=self._status.value,
        )
        
    def add_route(self, route_config: RouteConfig) -> None:
        """Add route configuration.
        
        Args:
            route_config: Route configuration
        """
        route_key = f"{route_config.method}:{route_config.path}"
        self._routes[route_key] = route_config
        
        # Initialize load balancer for service
        if route_config.target_service not in self._load_balancers:
            if route_config.load_balancer == "weighted":
                self._load_balancers[route_config.target_service] = WeightedLoadBalancer()
            else:
                self._load_balancers[route_config.target_service] = RoundRobinLoadBalancer()
                
        # Initialize circuit breaker
        if route_config.target_service not in self._circuit_breakers:
            self._circuit_breakers[route_config.target_service] = CircuitBreaker(
                threshold=route_config.circuit_breaker_threshold,
                timeout=60
            )
            
        _logger.debug("route_added", route=route_key, service=route_config.target_service)
        
    def add_service(self, service_config: ServiceConfig) -> None:
        """Add service configuration.
        
        Args:
            service_config: Service configuration
        """
        self._services[service_config.name] = service_config
        
        # Initialize load balancer
        if service_config.name not in self._load_balancers:
            if service_config.load_balancer == "weighted":
                self._load_balancers[service_config.name] = WeightedLoadBalancer()
            else:
                self._load_balancers[service_config.name] = RoundRobinLoadBalancer()
                
        # Initialize circuit breaker
        if service_config.name not in self._circuit_breakers:
            self._circuit_breakers[service_config.name] = CircuitBreaker(
                threshold=service_config.circuit_breaker_threshold,
                timeout=service_config.circuit_breaker_timeout
            )
            
        _logger.debug("service_added", service=service_config.name, endpoints=service_config.endpoints)
        
    async def process_request(self, request_info: RequestInfo) -> ResponseInfo:
        """Process incoming request.
        
        Args:
            request_info: Request information
            
        Returns:
            Response information
        """
        start_time = time.time()
        
        try:
            # Update statistics
            self._stats["total_requests"] += 1
            
            # Find matching route
            route = self._find_route(request_info.method, request_info.path)
            if not route:
                return self._create_error_response(404, "Route not found")
                
            # Check rate limiting
            if route.rate_limit_config:
                rate_limit_result = await self._rate_limiter.check_rate_limit(
                    route.rate_limit_config,
                    {
                        "user_id": request_info.headers.get("x-user-id"),
                        "ip": request_info.client_ip,
                        "endpoint": f"{request_info.method}:{request_info.path}",
                    }
                )
                
                if not rate_limit_result.allowed:
                    self._stats["rate_limit_blocks"] += 1
                    return self._create_error_response(
                        429, 
                        "Rate limit exceeded",
                        {"Retry-After": str(int(rate_limit_result.retry_after or 60))}
                    )
                    
            # Process with tracing
            async with self._tracer.start_span(
                f"{request_info.method} {request_info.path}",
                SpanKind.SERVER,
                attributes={
                    "http.method": request_info.method,
                    "http.url": request_info.path,
                    "http.user_agent": request_info.user_agent,
                    "client.ip": request_info.client_ip,
                }
            ) as span:
                
                # Set request context
                span.set_attribute("gateway.route", f"{route.method}:{route.path}")
                span.set_attribute("gateway.service", route.target_service)
                
                # Apply middleware pipeline
                if self._middleware_pipeline:
                    request_info = await self._middleware_pipeline.process_request(request_info)
                    
                # Route request to service
                response = await self._route_to_service(route, request_info)
                
                # Apply response middleware
                if self._middleware_pipeline:
                    response = await self._middleware_pipeline.process_response(response)
                    
                # Update span
                span.set_attribute("http.status_code", response.status_code)
                span.set_status("OK" if response.status_code < 400 else "ERROR")
                
                # Update statistics
                if response.status_code < 400:
                    self._stats["successful_requests"] += 1
                else:
                    self._stats["failed_requests"] += 1
                    
                # Update route usage
                route_key = f"{route.method}:{route.path}"
                self._stats["route_usage"][route_key] = self._stats["route_usage"].get(route_key, 0) + 1
                
                # Update service usage
                self._stats["service_usage"][route.target_service] = self._stats["service_usage"].get(route.target_service, 0) + 1
                
                return response
                
        except Exception as e:
            _logger.error("request_processing_failed", request_id=request_info.request_id, error=str(e))
            self._stats["failed_requests"] += 1
            return self._create_error_response(500, "Internal server error")
            
        finally:
            # Update response time statistics
            duration_ms = (time.time() - start_time) * 1000
            self._update_response_time_stats(duration_ms)
            
    def _find_route(self, method: str, path: str) -> Optional[RouteConfig]:
        """Find matching route for method and path.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            Matching route or None
        """
        route_key = f"{method}:{path}"
        return self._routes.get(route_key)
        
    async def _route_to_service(self, route: RouteConfig, request_info: RequestInfo) -> ResponseInfo:
        """Route request to target service.
        
        Args:
            route: Route configuration
            request_info: Request information
            
        Returns:
            Response from service
        """
        service = self._services.get(route.target_service)
        if not service or not service.enabled:
            return self._create_error_response(503, f"Service {route.target_service} not available")
            
        # Get load balancer
        load_balancer = self._load_balancers.get(route.target_service)
        if not load_balancer:
            return self._create_error_response(500, "Load balancer not configured")
            
        # Get circuit breaker
        circuit_breaker = self._circuit_breakers.get(route.target_service)
        
        # Select endpoint
        try:
            endpoint = load_balancer.select_endpoint(service.endpoints)
        except ValueError as e:
            return self._create_error_response(503, f"No healthy endpoints available: {str(e)}")
            
        # Make request with circuit breaker
        if circuit_breaker:
            return await circuit_breaker.call(
                endpoint,
                lambda: self._make_service_request(endpoint, route, request_info)
            )
        else:
            return await self._make_service_request(endpoint, route, request_info)
            
    async def _make_service_request(
        self, 
        endpoint: str, 
        route: RouteConfig, 
        request_info: RequestInfo
    ) -> ResponseInfo:
        """Make request to service endpoint.
        
        Args:
            endpoint: Service endpoint
            route: Route configuration
            request_info: Request information
            
        Returns:
            Service response
        """
        # This would implement actual HTTP request to service
        # For now, return a mock response
        
        await asyncio.sleep(0.01)  # Simulate network latency
        
        return ResponseInfo(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps({
                "message": "Request processed",
                "endpoint": endpoint,
                "path": request_info.path,
                "method": request_info.method,
            }).encode(),
            duration_ms=10.0,
        )
        
    def _create_error_response(self, status_code: int, message: str, headers: Optional[Dict[str, str]] = None) -> ResponseInfo:
        """Create error response.
        
        Args:
            status_code: HTTP status code
            message: Error message
            headers: Additional headers
            
        Returns:
            Error response
        """
        response_headers = {"Content-Type": "application/json"}
        if headers:
            response_headers.update(headers)
            
        return ResponseInfo(
            status_code=status_code,
            headers=response_headers,
            body=json.dumps({"error": message}).encode(),
        )
        
    def _create_default_rate_limit(self):
        """Create default rate limit configuration."""
        from mindflow_backend.infra.security.rate_limiter import RateLimitConfig, RateLimitScope
        
        return RateLimitConfig(
            algorithm=self._rate_limiter._algorithms.get("TOKEN_BUCKET"),
            scope=RateLimitScope.IP,
            limit=100,
            window_seconds=60,
        )
        
    def _update_response_time_stats(self, duration_ms: float) -> None:
        """Update response time statistics.
        
        Args:
            duration_ms: Response duration in milliseconds
        """
        current_avg = self._stats["avg_response_time_ms"]
        count = self._stats["total_requests"]
        
        if count == 0:
            self._stats["avg_response_time_ms"] = duration_ms
        else:
            self._stats["avg_response_time_ms"] = (current_avg * count + duration_ms) / (count + 1)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get gateway statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self._stats.copy()
        
        # Calculate success rate
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            
        # Add configuration info
        stats["routes_count"] = len(self._routes)
        stats["services_count"] = len(self._services)
        stats["status"] = self._status.value
        
        # Add circuit breaker states
        stats["circuit_breakers"] = {
            service: breaker.get_state()
            for service, breaker in self._circuit_breakers.items()
        }
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform gateway health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Check services
            healthy_services = 0
            total_services = len(self._services)
            
            for service_name, service in self._services.items():
                if service.enabled:
                    healthy_services += 1
                    
            # Check circuit breakers
            open_circuits = sum(
                1 for cb in self._circuit_breakers.values()
                if cb.get_state()["state"] == "OPEN"
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "services_healthy": healthy_services,
                "services_total": total_services,
                "open_circuits": open_circuits,
                "routes_count": len(self._routes),
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("api_gateway_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("api_gateway_health_check_failed", **error_data)
            return error_data


# Global API gateway instance
_api_gateway: Optional[APIGateway] = None


def get_api_gateway() -> APIGateway:
    """Get global API gateway instance.
    
    Returns:
        APIGateway instance
    """
    global _api_gateway
    if _api_gateway is None:
        _api_gateway = APIGateway()
    return _api_gateway
