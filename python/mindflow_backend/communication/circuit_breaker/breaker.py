"""
Circuit Breaker for MindFlow agent communication.

Provides fault tolerance for agent communication with
automatic recovery and fallback mechanisms.
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5           # Number of failures before opening
    recovery_timeout: int = 60           # Seconds before trying recovery
    success_threshold: int = 3           # Successes needed to close circuit
    timeout: int = 30                    # Request timeout in seconds
    fallback_enabled: bool = True        # Enable fallback mechanism


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for agent communication.
    
    Prevents cascading failures by opening the circuit when
    too many requests fail, and automatically recovering when
    the service becomes available again.
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._last_opened_time: Optional[datetime] = None
        self._fallback_handler: Optional[Callable] = None
    
    def set_fallback_handler(self, handler: Callable) -> None:
        """Set a fallback handler for when circuit is open."""
        self._fallback_handler = handler
    
    def can_execute(self) -> bool:
        """
        Check if a request can be executed.
        
        Returns:
            True if request can be executed
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_opened_time:
                elapsed = datetime.now() - self._last_opened_time
                if elapsed > timedelta(seconds=self.config.recovery_timeout):
                    logger.info(
                        f"Circuit {self.name}: Recovery timeout passed, "
                        "moving to HALF_OPEN"
                    )
                    self.state = CircuitState.HALF_OPEN
                    return True
            return False
        
        # HALF_OPEN state - allow limited requests
        return True
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.stats.total_requests += 1
        self.stats.successful_requests += 1
        self.stats.consecutive_successes += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                logger.info(
                    f"Circuit {self.name}: Success threshold reached, "
                    "closing circuit"
                )
                self.state = CircuitState.CLOSED
                self.stats.consecutive_successes = 0
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.stats.total_requests += 1
        self.stats.failed_requests += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        self.stats.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                logger.warning(
                    f"Circuit {self.name}: Failure threshold reached, "
                    "opening circuit"
                )
                self.state = CircuitState.OPEN
                self._last_opened_time = datetime.now()
                self.stats.circuit_opened_count += 1
        
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(
                f"Circuit {self.name}: Failure in HALF_OPEN state, "
                "reopening circuit"
            )
            self.state = CircuitState.OPEN
            self._last_opened_time = datetime.now()
    
    async def execute(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Execution result
        """
        if not self.can_execute():
            logger.warning(
                f"Circuit {self.name}: Circuit is OPEN, request blocked"
            )
            
            if self.config.fallback_enabled and self._fallback_handler:
                logger.info(f"Circuit {self.name}: Using fallback handler")
                return await self._fallback_handler(*args, **kwargs)
            
            return {
                "success": False,
                "error": f"Circuit {self.name} is OPEN",
                "circuit_state": self.state.value
            }
        
        try:
            result = await func(*args, **kwargs)
            
            if result.get("success", False):
                self.record_success()
            else:
                self.record_failure()
            
            return result
        
        except Exception as e:
            logger.error(f"Circuit {self.name}: Exception during execution: {e}")
            self.record_failure()
            
            if self.config.fallback_enabled and self._fallback_handler:
                logger.info(f"Circuit {self.name}: Using fallback handler")
                return await self._fallback_handler(*args, **kwargs)
            
            return {
                "success": False,
                "error": str(e),
                "circuit_state": self.state.value
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_requests": self.stats.total_requests,
            "successful_requests": self.stats.successful_requests,
            "failed_requests": self.stats.failed_requests,
            "circuit_opened_count": self.stats.circuit_opened_count,
            "consecutive_failures": self.stats.consecutive_failures,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": (
                self.stats.last_failure_time.isoformat()
                if self.stats.last_failure_time else None
            ),
            "last_success_time": (
                self.stats.last_success_time.isoformat()
                if self.stats.last_success_time else None
            ),
            "failure_rate": (
                self.stats.failed_requests / self.stats.total_requests * 100
                if self.stats.total_requests > 0 else 0
            )
        }
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._last_opened_time = None
        logger.info(f"Circuit {self.name}: Reset to CLOSED state")