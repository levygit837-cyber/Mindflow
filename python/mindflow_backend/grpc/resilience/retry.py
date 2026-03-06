"""Advanced retry policies for gRPC operations.

Provides sophisticated retry mechanisms including exponential backoff,
jitter, selective retry by error type, and custom retry strategies.
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field

import grpc
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE = "immediate"
    CUSTOM = "custom"


class RetryDecision(Enum):
    """Retry decision outcomes."""
    RETRY = "retry"
    STOP = "stop"
    FAIL_FAST = "fail_fast"


@dataclass
class RetryConfig:
    """Configuration for retry policies."""
    max_attempts: int = 3
    base_delay: float = 0.1          # Base delay in seconds
    max_delay: float = 30.0          # Maximum delay in seconds
    multiplier: float = 2.0          # Backoff multiplier
    jitter: bool = True              # Add jitter to prevent thundering herd
    jitter_factor: float = 0.1       # Jitter factor (0-1)
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Selective retry settings
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ConnectionError,
        TimeoutError,
        grpc.RpcError,
    ])
    non_retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ValueError,
        KeyError,
        PermissionError,
    ])
    retryable_grpc_codes: List[grpc.StatusCode] = field(default_factory=lambda: [
        grpc.StatusCode.UNAVAILABLE,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        grpc.StatusCode.RESOURCE_EXHAUSTED,
        grpc.StatusCode.INTERNAL,
    ])
    
    # Advanced settings
    retry_on_specific_errors: List[str] = field(default_factory=list)
    stop_on_specific_errors: List[str] = field(default_factory=list)
    custom_retry_condition: Optional[Callable[[Exception, int], bool]] = None


class RetryableError(Exception):
    """Base class for retryable errors."""
    pass


class NonRetryableError(Exception):
    """Base class for non-retryable errors."""
    pass


class RetryExhaustedError(Exception):
    """Raised when retry attempts are exhausted."""
    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts. Last error: {last_exception}")


class RetryPolicy(ABC):
    """Abstract base class for retry policies."""
    
    @abstractmethod
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with retry logic."""
        pass
    
    @abstractmethod
    def should_retry(self, exception: Exception, attempt: int) -> RetryDecision:
        """Determine if operation should be retried."""
        pass
    
    @abstractmethod
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry."""
        pass


class AdvancedRetryPolicy(RetryPolicy):
    """Advanced retry policy with configurable strategies and conditions."""
    
    def __init__(self, config: RetryConfig | None = None):
        self.config = config or RetryConfig()
        self._attempt_history: List[Dict[str, Any]] = []
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with advanced retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            attempt_start = time.time()
            
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Record successful attempt
                self._record_attempt(attempt + 1, time.time() - attempt_start, None, True)
                
                _logger.debug(
                    "retry_operation_success",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    duration=time.time() - attempt_start
                )
                
                return result
                
            except Exception as exc:
                last_exception = exc
                duration = time.time() - attempt_start
                
                # Record failed attempt
                self._record_attempt(attempt + 1, duration, exc, False)
                
                # Check if we should retry
                retry_decision = self.should_retry(exc, attempt + 1)
                
                if retry_decision == RetryDecision.FAIL_FAST:
                    _logger.warning(
                        "retry_fail_fast",
                        attempt=attempt + 1,
                        error=str(exc),
                        error_type=type(exc).__name__
                    )
                    raise exc
                
                if retry_decision == RetryDecision.STOP or attempt + 1 >= self.config.max_attempts:
                    _logger.error(
                        "retry_exhausted",
                        attempt=attempt + 1,
                        max_attempts=self.config.max_attempts,
                        final_error=str(exc),
                        error_type=type(exc).__name__
                    )
                    raise RetryExhaustedError(exc, attempt + 1) from exc
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt + 1)
                
                _logger.warning(
                    "retry_operation_failed",
                    attempt=attempt + 1,
                    max_attempts=self.config.max_attempts,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    retry_delay=delay
                )
                
                await asyncio.sleep(delay)
        
        # This should not be reached due to the loop logic
        raise RetryExhaustedError(last_exception or Exception("Unknown error"), self.config.max_attempts)
    
    def should_retry(self, exception: Exception, attempt: int) -> RetryDecision:
        """Determine if operation should be retried based on exception and attempt."""
        # Check custom retry condition first
        if self.config.custom_retry_condition:
            try:
                if not self.config.custom_retry_condition(exception, attempt):
                    return RetryDecision.STOP
            except Exception as exc:
                _logger.warning("custom_retry_condition_error", error=str(exc))
        
        # Check specific error messages
        error_message = str(exception).lower()
        
        # Stop on specific error messages
        for stop_error in self.config.stop_on_specific_errors:
            if stop_error.lower() in error_message:
                return RetryDecision.FAIL_FAST
        
        # Retry on specific error messages
        for retry_error in self.config.retry_on_specific_errors:
            if retry_error.lower() in error_message:
                return RetryDecision.RETRY
        
        # Check exception type hierarchy
        for non_retryable_exc in self.config.non_retryable_exceptions:
            if isinstance(exception, non_retryable_exc):
                return RetryDecision.FAIL_FAST
        
        # Check if exception is retryable
        for retryable_exc in self.config.retryable_exceptions:
            if isinstance(exception, retryable_exc):
                return RetryDecision.RETRY
        
        # Special handling for gRPC errors
        if isinstance(exception, grpc.RpcError):
            if exception.code() in self.config.retryable_grpc_codes:
                return RetryDecision.RETRY
            else:
                return RetryDecision.FAIL_FAST
        
        # Default: don't retry unknown exceptions
        return RetryDecision.STOP
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry based on strategy."""
        if self.config.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        
        elif self.config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = self.config.base_delay
        
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.multiplier ** (attempt - 1))
        
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay + jitter)
        
        return delay
    
    def _record_attempt(self, attempt: int, duration: float, error: Exception | None, success: bool):
        """Record attempt for statistics."""
        self._attempt_history.append({
            'attempt': attempt,
            'duration': duration,
            'error': str(error) if error else None,
            'error_type': type(error).__name__ if error else None,
            'success': success,
            'timestamp': time.time()
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retry statistics."""
        if not self._attempt_history:
            return {
                'total_attempts': 0,
                'successful_attempts': 0,
                'failed_attempts': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'config': self.config.__dict__
            }
        
        total_attempts = len(self._attempt_history)
        successful_attempts = sum(1 for a in self._attempt_history if a['success'])
        failed_attempts = total_attempts - successful_attempts
        success_rate = (successful_attempts / total_attempts) * 100
        average_duration = sum(a['duration'] for a in self._attempt_history) / total_attempts
        
        # Error distribution
        error_distribution = {}
        for attempt in self._attempt_history:
            if attempt['error_type']:
                error_distribution[attempt['error_type']] = error_distribution.get(attempt['error_type'], 0) + 1
        
        return {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': failed_attempts,
            'success_rate': success_rate,
            'average_duration': average_duration,
            'error_distribution': error_distribution,
            'config': self.config.__dict__
        }
    
    def reset_statistics(self):
        """Reset attempt history."""
        self._attempt_history.clear()


class ConditionalRetryPolicy(AdvancedRetryPolicy):
    """Retry policy with conditional logic based on operation context."""
    
    def __init__(self, config: RetryConfig | None = None, 
                 condition: Callable[[str, Dict[str, Any]], bool] | None = None):
        super().__init__(config)
        self.condition = condition
    
    async def execute_with_retry(self, operation: Callable, operation_name: str = "unknown", 
                               context: Dict[str, Any] | None = None, *args, **kwargs) -> Any:
        """Execute operation with conditional retry."""
        context = context or {}
        
        # Check if retry should be enabled for this operation
        if self.condition and not self.condition(operation_name, context):
            _logger.info("retry_disabled_by_condition", operation=operation_name, context=context)
            # Execute without retry
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        
        # Execute with retry
        return await super().execute_with_retry(operation, *args, **kwargs)


class RateLimitedRetryPolicy(AdvancedRetryPolicy):
    """Retry policy with rate limiting to prevent retry storms."""
    
    def __init__(self, config: RetryConfig | None = None, max_retries_per_second: float = 1.0):
        super().__init__(config)
        self.max_retries_per_second = max_retries_per_second
        self._retry_times: List[float] = []
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with rate-limited retry."""
        # Clean old retry times (older than 1 second)
        current_time = time.time()
        self._retry_times = [t for t in self._retry_times if current_time - t < 1.0]
        
        # Check if we've exceeded the retry rate limit
        if len(self._retry_times) >= self.max_retries_per_second:
            sleep_time = 1.0 - (current_time - self._retry_times[0])
            if sleep_time > 0:
                _logger.info("retry_rate_limit_sleep", sleep_time=sleep_time)
                await asyncio.sleep(sleep_time)
        
        # Record this retry attempt
        self._retry_times.append(current_time)
        
        # Execute with retry
        return await super().execute_with_retry(operation, *args, **kwargs)


# Predefined retry configurations
DEFAULT_RETRY_CONFIG = RetryConfig()
AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=0.05,
    max_delay=10.0,
    multiplier=1.5,
    jitter=True
)
CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=1.0,
    max_delay=5.0,
    multiplier=2.0,
    jitter=False
)
FAST_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.01,
    max_delay=1.0,
    multiplier=1.2,
    jitter=True,
    strategy=RetryStrategy.LINEAR_BACKOFF
)
