"""Load balancing strategies for gRPC service endpoints.

Provides multiple algorithms for distributing requests across
multiple service endpoints with health awareness and performance
optimization.
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class EndpointState(Enum):
    """Endpoint health states."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    UNKNOWN = "unknown"


@dataclass
class EndpointMetrics:
    """Performance metrics for an endpoint."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_request_time: float = 0.0
    consecutive_failures: int = 0
    last_success_time: float = 0.0
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    def get_average_response_time(self) -> float:
        """Calculate average response time."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests
    
    def record_request(self, success: bool, response_time: float):
        """Record request metrics."""
        self.total_requests += 1
        self.last_request_time = time.time()
        
        if success:
            self.successful_requests += 1
            self.total_response_time += response_time
            self.last_success_time = time.time()
            self.consecutive_failures = 0
        else:
            self.failed_requests += 1
            self.consecutive_failures += 1


@dataclass
class Endpoint:
    """Service endpoint with metadata and metrics."""
    id: str
    host: str
    port: int
    weight: float = 1.0
    state: EndpointState = EndpointState.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: EndpointMetrics = field(default_factory=EndpointMetrics)
    created_at: float = field(default_factory=time.time)
    last_health_check: float = 0.0
    
    def get_address(self) -> str:
        """Get endpoint address."""
        return f"{self.host}:{self.port}"
    
    def is_healthy(self) -> bool:
        """Check if endpoint is healthy."""
        return self.state == EndpointState.HEALTHY
    
    def is_available(self) -> bool:
        """Check if endpoint is available for requests."""
        return self.state in [EndpointState.HEALTHY, EndpointState.DRAINING]
    
    def record_selection(self):
        """Record endpoint selection."""
        # This can be used for selection-based metrics
        pass
    
    def get_active_connections(self) -> int:
        """Get active connections count."""
        # This would be tracked by the connection pool
        return 0
    
    def get_performance_metrics(self) -> EndpointMetrics:
        """Get performance metrics."""
        return self.metrics


@dataclass
class SelectionContext:
    """Context for endpoint selection."""
    request: Any = None
    available_endpoints: List[Endpoint] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LoadBalancingStrategy(ABC):
    """Abstract base class for load balancing strategies."""
    
    @abstractmethod
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select the best endpoint for the request."""
        pass
    
    @abstractmethod
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Update strategy statistics based on endpoint performance."""
        pass
    
    def get_name(self) -> str:
        """Get strategy name."""
        return self.__class__.__name__


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing strategy."""
    
    def __init__(self):
        self._current_index = 0
        self._lock = None  # Will be set when used in async context
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint using round-robin algorithm."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Select endpoint round-robin
        selected_endpoint = available_endpoints[self._current_index % len(available_endpoints)]
        self._current_index += 1
        
        selected_endpoint.record_selection()
        return selected_endpoint
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Round-robin doesn't use performance statistics."""
        pass


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Load balancing strategy that selects endpoint with least active connections."""
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint with least active connections."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Sort by active connections (ascending)
        sorted_endpoints = sorted(
            available_endpoints,
            key=lambda ep: ep.get_active_connections()
        )
        
        # Return endpoint with least connections
        selected_endpoint = sorted_endpoints[0]
        selected_endpoint.record_selection()
        
        return selected_endpoint
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Least connections strategy doesn't use performance statistics."""
        pass


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin strategy based on endpoint performance."""
    
    def __init__(self):
        self._weights: Dict[str, float] = {}
        self._current_weights: Dict[str, float] = {}
        self._lock = None
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint using weighted round-robin."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Update weights based on performance
        self._update_weights(available_endpoints)
        
        # Select endpoint using weighted round-robin
        selected_endpoint = self._select_weighted_endpoint(available_endpoints)
        selected_endpoint.record_selection()
        
        return selected_endpoint
    
    def _update_weights(self, endpoints: List[Endpoint]):
        """Update weights based on endpoint performance."""
        for endpoint in endpoints:
            performance = endpoint.get_performance_metrics()
            
            # Calculate weight based on success rate and latency
            success_rate = performance.get_success_rate()
            avg_latency = performance.get_average_response_time()
            
            # Higher weight for better performance
            if success_rate > 0 and avg_latency > 0:
                weight = (success_rate * 100) / avg_latency
            else:
                weight = endpoint.weight
            
            # Apply endpoint's configured weight
            weight *= endpoint.weight
            
            self._weights[endpoint.id] = max(weight, 0.1)  # Minimum weight
            
            # Initialize current weight if not exists
            if endpoint.id not in self._current_weights:
                self._current_weights[endpoint.id] = 0.0
    
    def _select_weighted_endpoint(self, endpoints: List[Endpoint]) -> Endpoint:
        """Select endpoint using weighted round-robin algorithm."""
        total_weight = sum(self._weights.get(ep.id, 1.0) for ep in endpoints)
        
        if total_weight == 0:
            return endpoints[0]
        
        # Add current weights to weights
        for endpoint in endpoints:
            self._current_weights[endpoint.id] += self._weights.get(endpoint.id, 1.0)
        
        # Find endpoint with highest current weight
        selected_endpoint = max(
            endpoints,
            key=lambda ep: self._current_weights.get(ep.id, 0.0)
        )
        
        # Subtract total weight from selected endpoint
        self._current_weights[selected_endpoint.id] -= total_weight
        
        return selected_endpoint
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Update weights based on performance."""
        # Weights are updated on each selection, but we can also update here
        # for more responsive weight adjustments
        self._weights[endpoint.id] = max(0.1, performance.get_success_rate() * 10)


class RandomStrategy(LoadBalancingStrategy):
    """Random load balancing strategy."""
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select random endpoint."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Select random endpoint
        selected_endpoint = random.choice(available_endpoints)
        selected_endpoint.record_selection()
        
        return selected_endpoint
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Random strategy doesn't use performance statistics."""
        pass


class PerformanceBasedStrategy(LoadBalancingStrategy):
    """Load balancing strategy based on endpoint performance metrics."""
    
    def __init__(self, response_time_weight: float = 0.6, success_rate_weight: float = 0.4):
        self.response_time_weight = response_time_weight
        self.success_rate_weight = success_rate_weight
        self._performance_scores: Dict[str, float] = {}
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint with best performance score."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Calculate performance scores
        scored_endpoints = []
        for endpoint in available_endpoints:
            score = self._calculate_performance_score(endpoint)
            scored_endpoints.append((endpoint, score))
        
        # Sort by score (descending)
        scored_endpoints.sort(key=lambda x: x[1], reverse=True)
        
        # Select best performing endpoint
        selected_endpoint = scored_endpoints[0][0]
        selected_endpoint.record_selection()
        
        return selected_endpoint
    
    def _calculate_performance_score(self, endpoint: Endpoint) -> float:
        """Calculate performance score for endpoint."""
        metrics = endpoint.get_performance_metrics()
        
        # Response time score (lower is better)
        avg_response_time = metrics.get_average_response_time()
        response_time_score = 1.0 / (1.0 + avg_response_time) if avg_response_time > 0 else 1.0
        
        # Success rate score (higher is better)
        success_rate = metrics.get_success_rate()
        success_rate_score = success_rate
        
        # Combined score
        combined_score = (
            response_time_score * self.response_time_weight +
            success_rate_score * self.success_rate_weight
        )
        
        # Store for debugging
        self._performance_scores[endpoint.id] = combined_score
        
        return combined_score
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Performance scores are calculated on-demand."""
        pass
    
    def get_performance_scores(self) -> Dict[str, float]:
        """Get current performance scores for all endpoints."""
        return self._performance_scores.copy()


class StickySessionStrategy(LoadBalancingStrategy):
    """Strategy that maintains session affinity."""
    
    def __init__(self, fallback_strategy: LoadBalancingStrategy):
        self.fallback_strategy = fallback_strategy
        self._session_mappings: Dict[str, str] = {}  # session_id -> endpoint_id
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint based on session affinity."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Check if we have a session mapping
        session_id = context.session_id or context.metadata.get("session_id")
        if session_id and session_id in self._session_mappings:
            endpoint_id = self._session_mappings[session_id]
            
            # Find the mapped endpoint
            for endpoint in endpoints:
                if endpoint.id == endpoint_id and endpoint.is_available():
                    endpoint.record_selection()
                    return endpoint
        
        # Use fallback strategy for new sessions or unavailable endpoints
        selected_endpoint = self.fallback_strategy.select_endpoint(endpoints, context)
        
        # Store session mapping
        if session_id:
            self._session_mappings[session_id] = selected_endpoint.id
        
        return selected_endpoint
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Update fallback strategy statistics."""
        self.fallback_strategy.update_statistics(endpoint, performance)
    
    def clear_session_mapping(self, session_id: str):
        """Clear session mapping."""
        self._session_mappings.pop(session_id, None)
    
    def get_session_mappings(self) -> Dict[str, str]:
        """Get current session mappings."""
        return self._session_mappings.copy()


class ConsistentHashStrategy(LoadBalancingStrategy):
    """Consistent hashing strategy for request distribution."""
    
    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self._hash_ring: List[int] = []
        self._hash_to_endpoint: Dict[int, str] = {}
        self._endpoints: Dict[str, Endpoint] = {}
    
    def select_endpoint(self, endpoints: List[Endpoint], context: SelectionContext) -> Endpoint:
        """Select endpoint using consistent hashing."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter available endpoints
        available_endpoints = [ep for ep in endpoints if ep.is_available()]
        if not available_endpoints:
            raise ValueError("No available endpoints")
        
        # Update hash ring if endpoints changed
        self._update_hash_ring(available_endpoints)
        
        # Generate hash key from context
        hash_key = self._generate_hash_key(context)
        
        # Find endpoint on hash ring
        endpoint_id = self._find_endpoint_on_ring(hash_key)
        
        if endpoint_id and endpoint_id in self._endpoints:
            selected_endpoint = self._endpoints[endpoint_id]
            selected_endpoint.record_selection()
            return selected_endpoint
        
        # Fallback to first available endpoint
        selected_endpoint = available_endpoints[0]
        selected_endpoint.record_selection()
        return selected_endpoint
    
    def _generate_hash_key(self, context: SelectionContext) -> str:
        """Generate hash key from context."""
        # Use session_id, user_id, or request metadata
        if context.session_id:
            return f"session:{context.session_id}"
        elif context.user_id:
            return f"user:{context.user_id}"
        elif context.request:
            # Try to extract consistent identifier from request
            request_str = str(context.request)
            return f"request:{hash(request_str)}"
        else:
            return f"timestamp:{context.timestamp}"
    
    def _update_hash_ring(self, endpoints: List[Endpoint]):
        """Update consistent hash ring."""
        current_endpoints = {ep.id: ep for ep in endpoints}
        
        # Check if endpoints changed
        if set(current_endpoints.keys()) == set(self._endpoints.keys()):
            return
        
        # Rebuild hash ring
        self._endpoints = current_endpoints
        self._hash_ring.clear()
        self._hash_to_endpoint.clear()
        
        for endpoint in endpoints:
            # Add virtual nodes for better distribution
            for i in range(self.virtual_nodes):
                virtual_key = f"{endpoint.id}:{i}"
                hash_value = hash(virtual_key) & 0x7FFFFFFF  # Ensure positive
                self._hash_ring.append(hash_value)
                self._hash_to_endpoint[hash_value] = endpoint.id
        
        # Sort hash ring
        self._hash_ring.sort()
    
    def _find_endpoint_on_ring(self, hash_key: str) -> Optional[str]:
        """Find endpoint for hash key on ring."""
        if not self._hash_ring:
            return None
        
        hash_value = hash(hash_key) & 0x7FFFFFFF  # Ensure positive
        
        # Find first hash value >= hash_value
        for ring_hash in self._hash_ring:
            if ring_hash >= hash_value:
                return self._hash_to_endpoint[ring_hash]
        
        # Wrap around to first element
        return self._hash_to_endpoint[self._hash_ring[0]]
    
    def update_statistics(self, endpoint: Endpoint, performance: EndpointMetrics) -> None:
        """Consistent hashing doesn't use performance statistics."""
        pass


# Strategy factory
class LoadBalancingStrategyFactory:
    """Factory for creating load balancing strategies."""
    
    _strategies = {
        "round_robin": RoundRobinStrategy,
        "least_connections": LeastConnectionsStrategy,
        "weighted_round_robin": WeightedRoundRobinStrategy,
        "random": RandomStrategy,
        "performance_based": PerformanceBasedStrategy,
        "consistent_hash": ConsistentHashStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_name: str, **kwargs) -> LoadBalancingStrategy:
        """Create load balancing strategy by name."""
        if strategy_name not in cls._strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(cls._strategies.keys())}")
        
        strategy_class = cls._strategies[strategy_name]
        
        # Handle special cases
        if strategy_name == "sticky_session":
            fallback_strategy_name = kwargs.pop("fallback_strategy", "round_robin")
            fallback_strategy = cls.create_strategy(fallback_strategy_name)
            return StickySessionStrategy(fallback_strategy)
        
        return strategy_class(**kwargs)
    
    @classmethod
    def list_strategies(cls) -> List[str]:
        """List available strategy names."""
        return list(cls._strategies.keys())
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type):
        """Register a custom strategy."""
        cls._strategies[name] = strategy_class
