"""Advanced request routing system.

Provides comprehensive request routing with pattern matching,
load balancing, health checking, and routing optimization.
"""

from __future__ import annotations

import asyncio
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime, UTC, timedelta
from enum import Enum
import json
import uuid
import weakref

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.tracing.tracer import get_tracer, SpanKind
from mindflow_backend.infra.api.gateway import RequestInfo, ResponseInfo, ServiceConfig

_logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """Routing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    HASH_BASED = "hash_based"
    GEOGRAPHIC = "geographic"
    CUSTOM = "custom"


class RouteMatchType(Enum):
    """Route matching types."""
    EXACT = "exact"
    PREFIX = "prefix"
    REGEX = "regex"
    GLOB = "glob"
    HEADER = "header"
    QUERY = "query"
    METHOD = "method"


@dataclass
class RouteMatch:
    """Route matching criteria."""
    type: RouteMatchType
    pattern: str
    priority: int = 1
    case_sensitive: bool = False
    invert: bool = False
    
    def matches(self, request_info: RequestInfo) -> bool:
        """Check if request matches criteria.
        
        Args:
            request_info: Request information
            
        Returns:
            True if matches
        """
        value = self._get_value(request_info)
        
        if value is None:
            return self.invert
            
        pattern = self.pattern if self.case_sensitive else self.pattern.lower()
        value_str = str(value) if self.case_sensitive else str(value).lower()
        
        match = False
        
        if self.type == RouteMatchType.EXACT:
            match = value_str == pattern
        elif self.type == RouteMatchType.PREFIX:
            match = value_str.startswith(pattern)
        elif self.type == RouteMatchType.REGEX:
            try:
                match = bool(re.search(pattern, value_str))
            except re.error:
                match = False
        elif self.type == RouteMatchType.GLOB:
            # Simple glob matching
            pattern_regex = pattern.replace('*', '.*').replace('?', '.')
            match = bool(re.search(f'^{pattern_regex}$', value_str))
        elif self.type == RouteMatchType.HEADER:
            match = value_str == pattern
        elif self.type == RouteMatchType.QUERY:
            match = value_str == pattern
        elif self.type == RouteMatchType.METHOD:
            match = value_str == pattern.upper()
            
        return match != self.invert
        
    def _get_value(self, request_info: RequestInfo) -> Optional[str]:
        """Get value to match against.
        
        Args:
            request_info: Request information
            
        Returns:
            Value to match
        """
        if self.type == RouteMatchType.EXACT:
            return request_info.path
        elif self.type == RouteMatchType.PREFIX:
            return request_info.path
        elif self.type == RouteMatchType.REGEX:
            return request_info.path
        elif self.type == RouteMatchType.GLOB:
            return request_info.path
        elif self.type == RouteMatchType.HEADER:
            # Extract from headers
            return request_info.headers.get(self.pattern)
        elif self.type == RouteMatchType.QUERY:
            # Extract from query parameters
            return request_info.query_params.get(self.pattern)
        elif self.type == RouteMatchType.METHOD:
            return request_info.method
            
        return None


@dataclass
class RouteRule:
    """Routing rule definition."""
    name: str
    matches: List[RouteMatch]
    target_service: str
    target_endpoint: Optional[str] = None
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    weight: float = 1.0
    priority: int = 1
    enabled: bool = True
    timeout_ms: int = 30000
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    match_count: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0
    
    def matches(self, request_info: RequestInfo) -> bool:
        """Check if request matches all criteria.
        
        Args:
            request_info: Request information
            
        Returns:
            True if all criteria match
        """
        return all(match.matches(request_info) for match in self.matches)
        
    def update_metrics(self, success: bool, response_time_ms: float) -> None:
        """Update routing metrics.
        
        Args:
            success: Request was successful
            response_time_ms: Response time in milliseconds
        """
        self.match_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        # Update average response time
        if self.match_count == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            self.avg_response_time_ms = (
                (self.avg_response_time_ms * (self.match_count - 1) + response_time_ms) / self.match_count
            )
            
    def get_success_rate(self) -> float:
        """Get success rate.
        
        Returns:
            Success rate (0.0-1.0)
        """
        if self.match_count == 0:
            return 0.0
        return self.success_count / self.match_count
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "matches": [
                {
                    "type": match.type.value,
                    "pattern": match.pattern,
                    "priority": match.priority,
                    "case_sensitive": match.case_sensitive,
                    "invert": match.invert,
                }
                for match in self.matches
            ],
            "target_service": self.target_service,
            "target_endpoint": self.target_endpoint,
            "strategy": self.strategy.value,
            "weight": self.weight,
            "priority": self.priority,
            "enabled": self.enabled,
            "timeout_ms": self.timeout_ms,
            "retry_attempts": self.retry_attempts,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "match_count": self.match_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.get_success_rate(),
        }


class RoutingStrategy(ABC):
    """Abstract routing strategy."""
    
    @abstractmethod
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select endpoint for request.
        
        Args:
            endpoints: Available endpoints
            rule: Routing rule
            request_info: Request information
            
        Returns:
            Selected endpoint
        """
        pass
        
    @abstractmethod
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Update endpoint metrics.
        
        Args:
            endpoint: Endpoint identifier
            success: Request was successful
            response_time_ms: Response time in milliseconds
        """
        pass


class RoundRobinStrategy(RoutingStrategy):
    """Round-robin routing strategy."""
    
    def __init__(self):
        """Initialize round-robin strategy."""
        self._current_index = 0
        
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select next endpoint in round-robin fashion."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        endpoint = endpoints[self._current_index % len(endpoints)]
        self._current_index += 1
        
        return endpoint
        
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Round-robin doesn't track metrics."""
        pass


class WeightedRoundRobinStrategy(RoutingStrategy):
    """Weighted round-robin routing strategy."""
    
    def __init__(self):
        """Initialize weighted round-robin strategy."""
        self._weights: Dict[str, float] = {}
        self._current_weights: Dict[str, float] = {}
        
    def set_weight(self, endpoint: str, weight: float) -> None:
        """Set endpoint weight.
        
        Args:
            endpoint: Endpoint identifier
            weight: Weight value
        """
        self._weights[endpoint] = weight
        self._current_weights[endpoint] = weight
        
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select endpoint based on weights."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Initialize weights if not set
        for endpoint in endpoints:
            if endpoint not in self._weights:
                self._weights[endpoint] = 1.0
                self._current_weights[endpoint] = 1.0
                
        # Select endpoint with highest current weight
        selected_endpoint = max(endpoints, key=lambda ep: self._current_weights.get(ep, 0))
        
        # Decrease current weight
        self._current_weights[selected_endpoint] -= 1.0
        
        # Replenish weights if all are depleted
        if all(weight <= 0 for weight in self._current_weights.values()):
            for endpoint in endpoints:
                self._current_weights[endpoint] = self._weights[endpoint]
                
        return selected_endpoint
        
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Update endpoint weight based on performance."""
        if not success:
            # Reduce weight for failed requests
            current_weight = self._weights.get(endpoint, 1.0)
            self._weights[endpoint] = max(0.1, current_weight * 0.9)
        elif response_time_ms > 1000:  # Slow response
            # Slightly reduce weight for slow responses
            current_weight = self._weights.get(endpoint, 1.0)
            self._weights[endpoint] = max(0.1, current_weight * 0.95)


class LeastConnectionsStrategy(RoutingStrategy):
    """Least connections routing strategy."""
    
    def __init__(self):
        """Initialize least connections strategy."""
        self._connections: Dict[str, int] = {}
        
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select endpoint with least connections."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Initialize connection counts
        for endpoint in endpoints:
            if endpoint not in self._connections:
                self._connections[endpoint] = 0
                
        # Select endpoint with minimum connections
        selected_endpoint = min(endpoints, key=lambda ep: self._connections.get(ep, 0))
        
        # Increment connection count
        self._connections[selected_endpoint] += 1
        
        return selected_endpoint
        
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Decrement connection count."""
        if endpoint in self._connections:
            self._connections[endpoint] = max(0, self._connections[endpoint] - 1)


class LeastResponseTimeStrategy(RoutingStrategy):
    """Least response time routing strategy."""
    
    def __init__(self):
        """Initialize least response time strategy."""
        self._response_times: Dict[str, List[float]] = {}
        self._max_samples = 100
        
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select endpoint with least average response time."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Initialize response times
        for endpoint in endpoints:
            if endpoint not in self._response_times:
                self._response_times[endpoint] = []
                
        # Calculate average response times
        avg_times = {}
        for endpoint in endpoints:
            times = self._response_times[endpoint]
            if times:
                avg_times[endpoint] = sum(times) / len(times)
            else:
                avg_times[endpoint] = float('inf')  # No data yet
                
        # Select endpoint with minimum average time
        selected_endpoint = min(endpoints, key=lambda ep: avg_times.get(ep, float('inf')))
        
        return selected_endpoint
        
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Update response time metrics."""
        if endpoint not in self._response_times:
            self._response_times[endpoint] = []
            
        self._response_times[endpoint].append(response_time_ms)
        
        # Keep only recent samples
        if len(self._response_times[endpoint]) > self._max_samples:
            self._response_times[endpoint] = self._response_times[endpoint][-self._max_samples:]


class HashBasedStrategy(RoutingStrategy):
    """Hash-based routing strategy."""
    
    def __init__(self):
        """Initialize hash-based strategy."""
        
    async def select_endpoint(self, endpoints: List[str], rule: RouteRule, request_info: RequestInfo) -> str:
        """Select endpoint based on hash of request attributes."""
        if not endpoints:
            raise ValueError("No endpoints available")
            
        # Create hash from request path and client IP
        hash_input = f"{request_info.path}:{request_info.client_ip}"
        hash_value = hash(hash_input)
        
        # Select endpoint based on hash
        index = hash_value % len(endpoints)
        return endpoints[index]
        
    def update_endpoint_metrics(self, endpoint: str, success: bool, response_time_ms: float) -> None:
        """Hash-based doesn't track metrics."""
        pass


class RequestRouter:
    """Advanced request routing system.
    
    Features:
    - Multiple routing strategies
    - Pattern matching and rule evaluation
    - Load balancing with health checking
    - Performance metrics and optimization
    - Dynamic rule management
    """
    
    def __init__(self):
        """Initialize request router."""
        self._rules: List[RouteRule] = []
        self._strategies: Dict[RoutingStrategy, RoutingStrategy] = {}
        self._services: Dict[str, ServiceConfig] = {}
        self._endpoint_health: Dict[str, bool] = {}
        self._tracer = get_tracer()
        self._is_initialized = False
        
        # Routing configuration
        self._default_strategy = RoutingStrategy.ROUND_ROBIN
        self._health_check_interval = 30
        self._max_rules = 1000
        self._rule_cache_ttl = 300  # 5 minutes
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_health_checking = False
        
        # Statistics
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rules_matched": 0,
            "avg_routing_time_ms": 0.0,
            "strategy_usage": {},
        }
        
    async def initialize(self) -> None:
        """Initialize request router."""
        await self._tracer.initialize()
        
        # Initialize routing strategies
        self._strategies = {
            RoutingStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            RoutingStrategy.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy(),
            RoutingStrategy.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
            RoutingStrategy.LEAST_RESPONSE_TIME: LeastResponseTimeStrategy(),
            RoutingStrategy.HASH_BASED: HashBasedStrategy(),
        }
        
        # Start health checking
        await self.start_health_checking()
        
        self._is_initialized = True
        
        _logger.info(
            "request_router_initialized",
            strategies_count=len(self._strategies),
            rules_count=len(self._rules),
            health_check_interval=self._health_check_interval,
        )
        
    async def start_health_checking(self) -> None:
        """Start endpoint health checking."""
        if self._is_health_checking:
            return
            
        self._is_health_checking = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        _logger.info("endpoint_health_checking_started")
        
    async def stop_health_checking(self) -> None:
        """Stop endpoint health checking."""
        if not self._is_health_checking:
            return
            
        self._is_health_checking = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        _logger.info("endpoint_health_checking_stopped")
        
    async def _health_check_loop(self) -> None:
        """Main health checking loop."""
        while self._is_health_checking:
            try:
                await self._check_endpoint_health()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("health_check_loop_error", error=str(e))
                await asyncio.sleep(5)
                
    async def _check_endpoint_health(self) -> None:
        """Check health of all endpoints."""
        for service_name, service in self._services.items():
            if not service.enabled:
                continue
                
            for endpoint in service.endpoints:
                try:
                    # Simple health check - would implement actual HTTP check
                    # For now, assume all endpoints are healthy
                    self._endpoint_health[endpoint] = True
                    
                except Exception as e:
                    _logger.warning("endpoint_health_check_failed", endpoint=endpoint, error=str(e))
                    self._endpoint_health[endpoint] = False
                    
    def add_rule(self, rule: RouteRule) -> None:
        """Add routing rule.
        
        Args:
            rule: Routing rule to add
        """
        if len(self._rules) >= self._max_rules:
            # Remove oldest rule
            self._rules.pop(0)
            
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        
        _logger.debug("routing_rule_added", name=rule.name, priority=rule.priority)
        
    def remove_rule(self, name: str) -> bool:
        """Remove routing rule.
        
        Args:
            name: Rule name
            
        Returns:
            True if rule was removed
        """
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                del self._rules[i]
                _logger.debug("routing_rule_removed", name=name)
                return True
        return False
        
    def add_service(self, service: ServiceConfig) -> None:
        """Add service configuration.
        
        Args:
            service: Service configuration
        """
        self._services[service.name] = service
        
        # Initialize endpoint health
        for endpoint in service.endpoints:
            self._endpoint_health[endpoint] = True
            
        _logger.debug("service_added", name=service.name, endpoints=len(service.endpoints))
        
    async def route_request(self, request_info: RequestInfo) -> Tuple[str, Optional[RouteRule]]:
        """Route request to appropriate service.
        
        Args:
            request_info: Request information
            
        Returns:
            Tuple of (selected endpoint, matching rule)
        """
        if not self._is_initialized:
            raise RuntimeError("Request router not initialized")
            
        start_time = time.time()
        
        try:
            # Update statistics
            self._stats["total_requests"] += 1
            
            # Find matching rule
            matching_rule = None
            for rule in self._rules:
                if rule.enabled and rule.matches(request_info):
                    matching_rule = rule
                    self._stats["rules_matched"] += 1
                    break
                    
            if not matching_rule:
                # No matching rule - return error
                self._stats["failed_requests"] += 1
                raise ValueError("No matching routing rule found")
                
            # Get service endpoints
            service = self._services.get(matching_rule.target_service)
            if not service or not service.enabled:
                self._stats["failed_requests"] += 1
                raise ValueError(f"Service {matching_rule.target_service} not available")
                
            # Filter healthy endpoints
            healthy_endpoints = [
                ep for ep in service.endpoints
                if self._endpoint_health.get(ep, True)
            ]
            
            if not healthy_endpoints:
                self._stats["failed_requests"] += 1
                raise ValueError(f"No healthy endpoints available for service {matching_rule.target_service}")
                
            # Get routing strategy
            strategy = self._strategies.get(matching_rule.strategy)
            if not strategy:
                strategy = self._strategies.get(self._default_strategy)
                
            if not strategy:
                raise ValueError(f"Routing strategy {matching_rule.strategy} not available")
                
            # Select endpoint
            selected_endpoint = await strategy.select_endpoint(healthy_endpoints, matching_rule, request_info)
            
            # Update strategy usage statistics
            strategy_name = matching_rule.strategy.value
            self._stats["strategy_usage"][strategy_name] = self._stats["strategy_usage"].get(strategy_name, 0) + 1
            
            # Update routing time statistics
            routing_time_ms = (time.time() - start_time) * 1000
            current_avg = self._stats["avg_routing_time_ms"]
            count = self._stats["total_requests"]
            self._stats["avg_routing_time_ms"] = (current_avg * (count - 1) + routing_time_ms) / count
            
            _logger.debug(
                "request_routed",
                rule=matching_rule.name,
                service=matching_rule.target_service,
                endpoint=selected_endpoint,
                strategy=matching_rule.strategy.value,
                routing_time_ms=routing_time_ms,
            )
            
            return selected_endpoint, matching_rule
            
        except Exception as e:
            routing_time_ms = (time.time() - start_time) * 1000
            _logger.error(
                "request_routing_failed",
                path=request_info.path,
                method=request_info.method,
                error=str(e),
                routing_time_ms=routing_time_ms,
            )
            raise
            
    async def update_routing_metrics(self, endpoint: str, rule: RouteRule, success: bool, response_time_ms: float) -> None:
        """Update routing metrics.
        
        Args:
            endpoint: Selected endpoint
            rule: Matching rule
            success: Request was successful
            response_time_ms: Response time in milliseconds
        """
        # Update rule metrics
        rule.update_metrics(success, response_time_ms)
        
        # Update strategy metrics
        strategy = self._strategies.get(rule.strategy)
        if strategy:
            strategy.update_endpoint_metrics(endpoint, success, response_time_ms)
            
        # Update statistics
        if success:
            self._stats["successful_requests"] += 1
        else:
            self._stats["failed_requests"] += 1
            
    def get_rule_by_name(self, name: str) -> Optional[RouteRule]:
        """Get rule by name.
        
        Args:
            name: Rule name
            
        Returns:
            Rule or None
        """
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None
        
    def get_rules_for_service(self, service_name: str) -> List[RouteRule]:
        """Get all rules for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            List of rules
        """
        return [rule for rule in self._rules if rule.target_service == service_name]
        
    def get_endpoint_health(self) -> Dict[str, bool]:
        """Get endpoint health status.
        
        Returns:
            Endpoint health status
        """
        return self._endpoint_health.copy()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics.
        
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
        stats["rules_count"] = len(self._rules)
        stats["services_count"] = len(self._services)
        stats["strategies_count"] = len(self._strategies)
        stats["healthy_endpoints"] = sum(1 for healthy in self._endpoint_health.values() if healthy)
        stats["total_endpoints"] = len(self._endpoint_health)
        
        # Add rule statistics
        rule_stats = []
        for rule in self._rules:
            rule_stats.append({
                "name": rule.name,
                "target_service": rule.target_service,
                "match_count": rule.match_count,
                "success_rate": rule.get_success_rate(),
                "avg_response_time_ms": rule.avg_response_time_ms,
                "enabled": rule.enabled,
            })
            
        stats["rules"] = rule_stats
        
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """Perform router health check.
        
        Returns:
            Health check results
        """
        try:
            start_time = time.time()
            
            # Test routing functionality
            test_request = RequestInfo(
                request_id=str(uuid.uuid4()),
                method="GET",
                path="/health",
                headers={},
                query_params={},
                client_ip="127.0.0.1",
            )
            
            try:
                endpoint, rule = await self.route_request(test_request)
                routing_healthy = True
            except Exception:
                routing_healthy = False
                
            duration_ms = (time.time() - start_time) * 1000
            
            health_data = {
                "status": "healthy",
                "routing_healthy": routing_healthy,
                "rules_count": len(self._rules),
                "services_count": len(self._services),
                "healthy_endpoints": sum(1 for healthy in self._endpoint_health.values() if healthy),
                "total_endpoints": len(self._endpoint_health),
                "health_checking_active": self._is_health_checking,
                "duration_ms": duration_ms,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.info("request_router_health_check_success", **health_data)
            return health_data
            
        except Exception as e:
            error_data = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            
            _logger.error("request_router_health_check_failed", **error_data)
            return error_data


# Global request router instance
_request_router: Optional[RequestRouter] = None


def get_request_router() -> RequestRouter:
    """Get global request router instance.
    
    Returns:
        RequestRouter instance
    """
    global _request_router
    if _request_router is None:
        _request_router = RequestRouter()
    return _request_router
