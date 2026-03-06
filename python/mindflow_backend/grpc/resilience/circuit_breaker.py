"""gRPC circuit breaker implementation.

Provides circuit breaker pattern to prevent cascading failures
and enable automatic recovery when services become healthy again.
"""

from __future__ import annotations

import asyncio
import random
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 60.0      # Seconds to wait before trying again
    success_threshold: int = 3          # Successes needed to close circuit
    timeout: float = 30.0              # Timeout for individual calls
    max_half_open_calls: int = 10       # Max calls in half-open state
    monitor_period: float = 10.0        # Period to monitor health


@dataclass
class CallResult:
    """Result of a circuit breaker protected call."""
    success: bool
    duration: float
    error: Optional[Exception] = None
    circuit_state: CircuitState = CircuitState.CLOSED


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class GrpcCircuitBreaker:
    """gRPC circuit breaker implementation with state management."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None
        self._half_open_calls = 0
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes: Dict[str, float] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        _logger.info("circuit_breaker_created", name=name, config=self.config.__dict__)
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with circuit breaker protection."""
        async with self._lock:
            if self._should_attempt_call():
                return await self._execute_with_protection(operation, *args, **kwargs)
            else:
                self._record_call_attempt(False, 0, CircuitBreakerOpenError())
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is OPEN")
    
    def _should_attempt_call(self) -> bool:
        """Check if call should be attempted based on circuit state."""
        if self._state == CircuitState.CLOSED:
            return True
        
        elif self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self._last_failure_time and 
                time.time() - self._last_failure_time >= self.config.recovery_timeout):
                self._transition_to_half_open()
                return True
            return False
        
        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self._half_open_calls < self.config.max_half_open_calls
        
        return False
    
    async def _execute_with_protection(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with timeout and error handling."""
        start_time = time.time()
        self._total_calls += 1
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                operation(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            # Record success
            duration = time.time() - start_time
            self._record_success(duration)
            
            return result
            
        except asyncio.TimeoutError as exc:
            duration = time.time() - start_time
            self._record_failure(duration, exc)
            raise
        
        except Exception as exc:
            duration = time.time() - start_time
            self._record_failure(duration, exc)
            raise
    
    def _record_success(self, duration: float):
        """Record successful operation."""
        self._total_successes += 1
        self._last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0
        
        _logger.debug(
            "circuit_breaker_success",
            name=self.name,
            state=self._state.value,
            duration=duration,
            failure_count=self._failure_count,
            success_count=self._success_count
        )
    
    def _record_failure(self, duration: float, error: Exception):
        """Record failed operation."""
        self._total_failures += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state opens the circuit again
            self._transition_to_open()
        
        _logger.warning(
            "circuit_breaker_failure",
            name=self.name,
            state=self._state.value,
            duration=duration,
            error=str(error),
            failure_count=self._failure_count
        )
    
    def _record_call_attempt(self, success: bool, duration: float, error: Exception | None = None):
        """Record call attempt for statistics."""
        self._total_calls += 1
        if success:
            self._total_successes += 1
        else:
            self._total_failures += 1
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._state_changes[f'open_{time.time()}'] = self._failure_count
        
        _logger.warning(
            "circuit_breaker_opened",
            name=self.name,
            previous_state=old_state.value,
            failure_count=self._failure_count,
            failures_threshold=self.config.failure_threshold
        )
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._half_open_calls = 0
        self._state_changes[f'half_open_{time.time()}'] = self._failure_count
        
        _logger.info(
            "circuit_breaker_half_open",
            name=self.name,
            previous_state=old_state.value,
            recovery_timeout=self.config.recovery_timeout
        )
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._state_changes[f'closed_{time.time()}'] = self._total_successes
        
        _logger.info(
            "circuit_breaker_closed",
            name=self.name,
            previous_state=old_state.value,
            success_threshold=self.config.success_threshold
        )
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        success_rate = (self._total_successes / max(self._total_calls, 1)) * 100
        
        return {
            'name': self.name,
            'state': self._state.value,
            'failure_count': self._failure_count,
            'success_count': self._success_count,
            'total_calls': self._total_calls,
            'total_successes': self._total_successes,
            'total_failures': self._total_failures,
            'success_rate_percent': success_rate,
            'last_failure_time': self._last_failure_time,
            'last_success_time': self._last_success_time,
            'state_changes': self._state_changes,
            'config': self.config.__dict__
        }
    
    def force_open(self):
        """Force circuit to open state (for testing)."""
        self._transition_to_open()
    
    def force_close(self):
        """Force circuit to closed state (for testing)."""
        self._transition_to_closed()
    
    def reset(self):
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        self._half_open_calls = 0
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._state_changes.clear()
        
        _logger.info("circuit_breaker_reset", name=self.name)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._circuit_breakers: Dict[str, GrpcCircuitBreaker] = {}
    
    def get_circuit_breaker(self, name: str, config: CircuitBreakerConfig | None = None) -> GrpcCircuitBreaker:
        """Get or create circuit breaker."""
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = GrpcCircuitBreaker(name, config)
        return self._circuit_breakers[name]
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: cb.get_statistics() 
            for name, cb in self._circuit_breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for cb in self._circuit_breakers.values():
            cb.reset()
    
    def force_open_all(self):
        """Force all circuit breakers to open (for testing)."""
        for cb in self._circuit_breakers.values():
            cb.force_open()
    
    def force_close_all(self):
        """Force all circuit breakers to close (for testing)."""
        for cb in self._circuit_breakers.values():
            cb.force_close()


# Global circuit breaker registry
_circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, config: CircuitBreakerConfig | None = None) -> GrpcCircuitBreaker:
    """Get circuit breaker from global registry."""
    return _circuit_breaker_registry.get_circuit_breaker(name, config)


def get_all_circuit_breaker_statistics() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return _circuit_breaker_registry.get_all_statistics()


def reset_all_circuit_breakers():
    """Reset all circuit breakers."""
    _circuit_breaker_registry.reset_all()
