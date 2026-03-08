"""Fallback handler interface.

Defines contracts for fallback mechanisms including service failover,
alternative implementations, and graceful degradation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Callable, Union
from abc import abstractmethod
from enum import Enum

from mindflow_backend.schemas.errors import ErrorSchema


class FallbackStrategy(str, Enum):
    """Fallback strategy types."""
    PRIMARY_ONLY = "primary_only"          # Only try primary service
    FALLBACK_ON_FAILURE = "fallback_on_failure"  # Use fallback on primary failure
    LOAD_BALANCE = "load_balance"          # Load balance between primary and fallback
    HEALTH_CHECK = "health_check"          # Use health check to select
    CUSTOM = "custom"                      # Custom selection logic


@runtime_checkable
class FallbackHandlerContract(Protocol):
    """Contract for fallback handler implementation.
    
    Provides fallback mechanisms for service failures, including
    failover, alternative implementations, and graceful degradation.
    """

    @abstractmethod
    async def execute_with_fallback(
        self,
        primary_operation: Callable,
        fallback_operations: List[Callable],
        *,
        strategy: FallbackStrategy = FallbackStrategy.FALLBACK_ON_FAILURE,
        timeout: Optional[float] = None,
        health_check: Optional[Callable] = None,
        **operation_kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute operation with fallback support.
        
        Args:
            primary_operation: Primary operation to try first
            fallback_operations: List of fallback operations
            strategy: Fallback selection strategy
            timeout: Operation timeout
            health_check: Health check function for services
            **operation_kwargs: Arguments to pass to operations
            
        Returns:
            Execution result with fallback information
        """
        ...

    @abstractmethod
    def register_fallback(
        self,
        service_name: str,
        fallback_operation: Callable,
        *,
        priority: int = 1,
        conditions: Optional[List[Callable]] = None,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a fallback operation for a service.
        
        Args:
            service_name: Name of the primary service
            fallback_operation: Fallback operation to register
            priority: Fallback priority (lower = higher priority)
            conditions: Conditions for using this fallback
            enabled: Whether fallback is enabled
            metadata: Additional metadata
        """
        ...

    @abstractmethod
    def get_fallback_operations(
        self,
        service_name: str,
        *,
        enabled_only: bool = True,
        healthy_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get registered fallback operations for a service.
        
        Args:
            service_name: Name of the service
            enabled_only: Only return enabled fallbacks
            healthy_only: Only return healthy fallbacks
            
        Returns:
            List of fallback operations with metadata
        """
        ...

    @abstractmethod
    async def check_fallback_health(
        self,
        service_name: str,
        fallback_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check health of fallback operations.
        
        Args:
            service_name: Name of the primary service
            fallback_name: Specific fallback to check
            
        Returns:
            Health check results
        """
        ...

    @abstractmethod
    def select_fallback(
        self,
        service_name: str,
        strategy: FallbackStrategy,
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Callable]:
        """Select fallback operation based on strategy.
        
        Args:
            service_name: Name of the primary service
            strategy: Selection strategy
            context: Additional context for selection
            
        Returns:
            Selected fallback operation or None
        """
        ...

    @abstractmethod
    async def execute_fallback(
        self,
        fallback_operation: Callable,
        *,
        timeout: Optional[float] = None,
        **operation_kwargs: Any,
    ) -> Dict[str, Any]:
        """Execute a fallback operation.
        
        Args:
            fallback_operation: Fallback operation to execute
            timeout: Operation timeout
            **operation_kwargs: Arguments to pass to operation
            
        Returns:
            Fallback execution result
        """
        ...

    @abstractmethod
    def get_fallback_statistics(
        self,
        service_name: Optional[str] = None,
        time_range: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get fallback usage statistics.
        
        Args:
            service_name: Specific service to get stats for
            time_range: Time range for statistics
            
        Returns:
            Fallback statistics
        """
        ...

    @abstractmethod
    def configure_fallback_strategy(
        self,
        service_name: str,
        strategy: FallbackStrategy,
        *,
        timeout: Optional[float] = None,
        max_attempts: int = 3,
        health_check_interval: float = 30.0,
    ) -> None:
        """Configure fallback strategy for a service.
        
        Args:
            service_name: Name of the service
            strategy: Fallback strategy to use
            timeout: Operation timeout
            max_attempts: Maximum fallback attempts
            health_check_interval: Health check interval
        """
        ...

    @abstractmethod
    async def test_all_fallbacks(
        self,
        service_name: str,
    ) -> Dict[str, Any]:
        """Test all registered fallback operations for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Test results for all fallbacks
        """
        ...

    # Fallback-specific convenience methods
    
    def create_fallback_config(
        self,
        strategy: FallbackStrategy = FallbackStrategy.FALLBACK_ON_FAILURE,
        timeout: Optional[float] = None,
        max_attempts: int = 3,
        health_check_interval: float = 30.0,
    ) -> Dict[str, Any]:
        """Create a fallback configuration.
        
        Args:
            strategy: Fallback selection strategy
            timeout: Operation timeout
            max_attempts: Maximum fallback attempts
            health_check_interval: Health check interval
            
        Returns:
            Fallback configuration
        """
        return {
            "strategy": strategy,
            "timeout": timeout,
            "max_attempts": max_attempts,
            "health_check_interval": health_check_interval,
        }

    def simulate_fallback_behavior(
        self,
        service_name: str,
        primary_failure_rate: float,
        fallback_failure_rate: float,
        total_requests: int = 100,
        strategy: FallbackStrategy = FallbackStrategy.FALLBACK_ON_FAILURE,
    ) -> Dict[str, Any]:
        """Simulate fallback behavior under failure conditions.
        
        Args:
            service_name: Name of the service
            primary_failure_rate: Primary service failure rate (0.0 to 1.0)
            fallback_failure_rate: Fallback service failure rate (0.0 to 1.0)
            total_requests: Total requests to simulate
            strategy: Fallback strategy to simulate
            
        Returns:
            Simulation results
        """
        import random
        
        results = {
            "service": service_name,
            "strategy": strategy.value,
            "primary_failure_rate": primary_failure_rate,
            "fallback_failure_rate": fallback_failure_rate,
            "total_requests": total_requests,
            "primary_successes": 0,
            "primary_failures": 0,
            "fallback_successes": 0,
            "fallback_failures": 0,
            "total_failures": 0,
            "success_rate": 0.0,
        }
        
        for _ in range(total_requests):
            # Try primary operation
            if random.random() >= primary_failure_rate:
                results["primary_successes"] += 1
            else:
                results["primary_failures"] += 1
                
                # Try fallback if strategy supports it
                if strategy in [FallbackStrategy.FALLBACK_ON_FAILURE, FallbackStrategy.LOAD_BALANCE]:
                    if random.random() >= fallback_failure_rate:
                        results["fallback_successes"] += 1
                    else:
                        results["fallback_failures"] += 1
                else:
                    results["total_failures"] += 1
        
        # Calculate success rate
        total_successes = results["primary_successes"] + results["fallback_successes"]
        results["success_rate"] = total_successes / total_requests
        results["total_failures"] = total_requests - total_successes
        
        return results

    def get_fallback_health_report(
        self,
        service_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get health report for fallback services.
        
        Args:
            service_names: List of services to include
            
        Returns:
            Fallback health report
        """
        # Default implementation - subclasses should override
        return {
            "timestamp": None,  # Would be current timestamp
            "services": {},
            "overall_health": "unknown",
            "total_fallbacks": 0,
            "healthy_fallbacks": 0,
            "unhealthy_fallbacks": 0,
        }

    def create_fallback_decorator(
        self,
        service_name: str,
        fallback_operations: List[Callable],
        strategy: FallbackStrategy = FallbackStrategy.FALLBACK_ON_FAILURE,
        config: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """Create a fallback decorator.
        
        Args:
            service_name: Name of the primary service
            fallback_operations: List of fallback operations
            strategy: Fallback selection strategy
            config: Fallback configuration
            
        Returns:
            Fallback decorator function
        """
        if config is None:
            config = self.create_fallback_config(strategy=strategy)
        
        # Register fallbacks
        for i, fallback in enumerate(fallback_operations):
            self.register_fallback(
                service_name,
                fallback,
                priority=i + 1,
            )
        
        def fallback_decorator(primary_func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                return await self.execute_with_fallback(
                    primary_func,
                    fallback_operations,
                    strategy=strategy,
                    timeout=config.get("timeout"),
                    **kwargs
                )
            return wrapper
        
        return fallback_decorator

    def optimize_fallback_strategy(
        self,
        service_name: str,
        historical_performance: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Optimize fallback strategy based on performance data.
        
        Args:
            service_name: Name of the service
            historical_performance: Historical performance data
            
        Returns:
            Optimized strategy recommendation
        """
        # Default implementation - subclasses should override
        return {
            "service": service_name,
            "recommended_strategy": FallbackStrategy.FALLBACK_ON_FAILURE,
            "reasoning": "Standard fallback strategy provides good balance",
            "expected_improvement": "Reliable fallback with minimal overhead",
            "configuration": self.create_fallback_config(),
        }

    def create_graceful_degradation_plan(
        self,
        service_name: str,
        degradation_levels: List[str],
    ) -> Dict[str, Any]:
        """Create a graceful degradation plan.
        
        Args:
            service_name: Name of the service
            degradation_levels: List of degradation levels
            
        Returns:
            Degradation plan
        """
        return {
            "service": service_name,
            "degradation_levels": degradation_levels,
            "plan": {
                level: {
                    "fallbacks": [],
                    "functionality": "full",
                    "performance_impact": "none",
                }
                for level in degradation_levels
            },
            "triggers": {},
            "recovery_procedures": {},
        }
