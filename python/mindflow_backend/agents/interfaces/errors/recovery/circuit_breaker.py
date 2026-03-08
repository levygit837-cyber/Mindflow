"""Circuit breaker interface.

Defines contracts for circuit breaker pattern implementation including
state management, threshold monitoring, and automatic recovery.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Dict, Optional, List, Callable
from abc import abstractmethod
from enum import Enum

from mindflow_backend.schemas.errors import ErrorSchema


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, blocking calls
    HALF_OPEN = "half_open"  # Testing if service has recovered


@runtime_checkable
class CircuitBreakerContract(Protocol):
    """Contract for circuit breaker implementation.
    
    Provides circuit breaker pattern functionality to prevent cascading
    failures and enable automatic service recovery.
    """

    @abstractmethod
    async def call_through_circuit(
        self,
        operation: Callable,
        *,
        service_name: str,
        timeout: Optional[float] = None,
        fallback: Optional[Callable] = None,
        **operation_kwargs: Any,
    ) -> Any:
        """Execute an operation through the circuit breaker.
        
        Args:
            operation: The operation to execute
            service_name: Name of the protected service
            timeout: Operation timeout
            fallback: Fallback operation when circuit is open
            **operation_kwargs: Arguments to pass to operation
            
        Returns:
            Operation result or fallback result
            
        Raises:
            Exception: If operation fails and no fallback provided
        """
        ...

    @abstractmethod
    def get_circuit_state(
        self,
        service_name: str,
    ) -> CircuitState:
        """Get current circuit state for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Current circuit state
        """
        ...

    @abstractmethod
    def record_success(
        self,
        service_name: str,
        *,
        response_time: Optional[float] = None,
    ) -> None:
        """Record a successful operation for circuit breaker metrics.
        
        Args:
            service_name: Name of the service
            response_time: Operation response time
        """
        ...

    @abstractmethod
    def record_failure(
        self,
        service_name: str,
        error: Exception,
        *,
        response_time: Optional[float] = None,
    ) -> None:
        """Record a failed operation for circuit breaker metrics.
        
        Args:
            service_name: Name of the service
            error: The error that occurred
            response_time: Operation response time
        """
        ...

    @abstractmethod
    def should_allow_request(
        self,
        service_name: str,
    ) -> bool:
        """Determine if a request should be allowed through the circuit.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if request should be allowed
        """
        ...

    @abstractmethod
    def configure_circuit_breaker(
        self,
        service_name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: float = 30.0,
        max_requests: Optional[int] = None,
        window_size: int = 100,
    ) -> None:
        """Configure circuit breaker parameters for a service.
        
        Args:
            service_name: Name of the service
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            success_threshold: Successes needed to close circuit
            timeout: Operation timeout
            max_requests: Max requests in half-open state
            window_size: Sliding window size for metrics
        """
        ...

    @abstractmethod
    async def reset_circuit(
        self,
        service_name: str,
    ) -> bool:
        """Manually reset circuit breaker to closed state.
        
        Args:
            service_name: Name of the service
            
        Returns:
            True if circuit was successfully reset
        """
        ...

    @abstractmethod
    def get_circuit_metrics(
        self,
        service_name: str,
    ) -> Dict[str, Any]:
        """Get circuit breaker metrics for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Circuit breaker metrics
        """
        ...

    @abstractmethod
    def get_all_circuit_states(
        self,
    ) -> Dict[str, CircuitState]:
        """Get circuit states for all configured services.
        
        Returns:
            Dictionary of service names to circuit states
        """
        ...

    @abstractmethod
    def register_state_change_callback(
        self,
        callback: Callable[[str, CircuitState, CircuitState], None],
        *,
        service_name: Optional[str] = None,
    ) -> None:
        """Register callback for circuit state changes.
        
        Args:
            callback: Callback function
            service_name: Specific service to monitor (None for all)
        """
        ...

    # Circuit breaker-specific convenience methods
    
    def create_circuit_config(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        timeout: float = 30.0,
        max_requests: Optional[int] = None,
        window_size: int = 100,
    ) -> Dict[str, Any]:
        """Create a circuit breaker configuration.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before trying half-open state
            success_threshold: Successes needed to close circuit
            timeout: Operation timeout
            max_requests: Max requests in half-open state
            window_size: Sliding window size for metrics
            
        Returns:
            Circuit breaker configuration
        """
        return {
            "failure_threshold": failure_threshold,
            "recovery_timeout": recovery_timeout,
            "success_threshold": success_threshold,
            "timeout": timeout,
            "max_requests": max_requests,
            "window_size": window_size,
        }

    def simulate_circuit_behavior(
        self,
        service_name: str,
        failure_rate: float,
        total_requests: int = 100,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Simulate circuit breaker behavior under failure conditions.
        
        Args:
            service_name: Name of the service
            failure_rate: Failure rate (0.0 to 1.0)
            total_requests: Total number of requests to simulate
            config: Circuit breaker configuration
            
        Returns:
            Simulation results
        """
        import random
        import time
        
        if config is None:
            config = self.create_circuit_config()
        
        # Configure circuit for simulation
        self.configure_circuit_breaker(service_name, **config)
        
        results = {
            "service": service_name,
            "failure_rate": failure_rate,
            "total_requests": total_requests,
            "successful_requests": 0,
            "failed_requests": 0,
            "blocked_requests": 0,
            "circuit_state_changes": [],
            "final_state": None,
        }
        
        current_state = CircuitState.CLOSED
        
        for i in range(total_requests):
            # Simulate request
            should_fail = random.random() < failure_rate
            
            if self.should_allow_request(service_name):
                try:
                    if should_fail:
                        self.record_failure(service_name, Exception("Simulated failure"))
                        results["failed_requests"] += 1
                    else:
                        self.record_success(service_name, response_time=random.uniform(0.1, 1.0))
                        results["successful_requests"] += 1
                except:
                    results["failed_requests"] += 1
            else:
                results["blocked_requests"] += 1
            
            # Check for state changes
            new_state = self.get_circuit_state(service_name)
            if new_state != current_state:
                results["circuit_state_changes"].append({
                    "request_number": i + 1,
                    "from_state": current_state,
                    "to_state": new_state,
                })
                current_state = new_state
        
        results["final_state"] = self.get_circuit_state(service_name)
        results["circuit_metrics"] = self.get_circuit_metrics(service_name)
        
        return results

    def get_circuit_health_report(
        self,
        service_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get health report for circuit breakers.
        
        Args:
            service_names: List of services to include (None for all)
            
        Returns:
            Circuit breaker health report
        """
        all_states = self.get_all_circuit_states()
        
        if service_names:
            states = {name: state for name, state in all_states.items() if name in service_names}
        else:
            states = all_states
        
        report = {
            "timestamp": None,  # Would be current timestamp
            "total_services": len(states),
            "closed_services": len([s for s in states.values() if s == CircuitState.CLOSED]),
            "open_services": len([s for s in states.values() if s == CircuitState.OPEN]),
            "half_open_services": len([s for s in states.values() if s == CircuitState.HALF_OPEN]),
            "services": {},
        }
        
        for service_name, state in states.items():
            metrics = self.get_circuit_metrics(service_name)
            report["services"][service_name] = {
                "state": state.value,
                "health": "healthy" if state == CircuitState.CLOSED else "degraded",
                "metrics": metrics,
            }
        
        return report

    def optimize_circuit_config(
        self,
        service_name: str,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Optimize circuit breaker configuration based on historical data.
        
        Args:
            service_name: Name of the service
            historical_data: Historical failure data
            
        Returns:
            Optimized configuration with reasoning
        """
        # Default implementation - subclasses should override with actual optimization
        return {
            "service": service_name,
            "optimized_config": self.create_circuit_config(
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=3,
            ),
            "reasoning": "Default configuration based on standard practices",
            "expected_improvement": "Balanced sensitivity and recovery time",
            "confidence": 0.7,
        }

    def create_circuit_decorator(
        self,
        service_name: str,
        config: Optional[Dict[str, Any]] = None,
        fallback: Optional[Callable] = None,
    ) -> Callable:
        """Create a circuit breaker decorator.
        
        Args:
            service_name: Name of the protected service
            config: Circuit breaker configuration
            fallback: Fallback operation
            
        Returns:
            Circuit breaker decorator function
        """
        if config is None:
            config = self.create_circuit_config()
        
        self.configure_circuit_breaker(service_name, **config)
        
        def circuit_breaker_decorator(func: Callable) -> Callable:
            async def wrapper(*args, **kwargs):
                return await self.call_through_circuit(
                    func,
                    service_name=service_name,
                    fallback=fallback,
                    **kwargs
                )
            return wrapper
        
        return circuit_breaker
