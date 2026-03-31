"""Advanced retry policies with adaptive backoff and intelligent retry logic.

Provides sophisticated retry mechanisms including adaptive backoff,
performance-based tuning, circuit breaker integration, and comprehensive metrics.
"""

from __future__ import annotations

import asyncio
import random
import statistics
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.grpc.resilience.retry import (
    RetryableError,
    RetryConfig,
    RetryDecision,
)
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AdaptiveBackoffType(Enum):
    """Types of adaptive backoff strategies."""
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"
    LINEAR = "linear"
    ADAPTIVE = "adaptive"
    PERFORMANCE_BASED = "performance_based"


class RetryConditionType(Enum):
    """Types of retry conditions."""
    ALWAYS = "always"
    ON_ERROR_TYPE = "on_error_type"
    ON_STATUS_CODE = "on_status_code"
    ON_RESPONSE_TIME = "on_response_time"
    CUSTOM_PREDICATE = "custom_predicate"


@dataclass
class AdvancedRetryConfig(RetryConfig):
    """Enhanced configuration for advanced retry policies."""
    
    # Adaptive backoff settings
    adaptive_backoff_type: AdaptiveBackoffType = AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER
    enable_adaptive_delay: bool = True
    performance_window_size: int = 50
    min_adaptive_delay: float = 0.01
    max_adaptive_delay: float = 10.0
    
    # Retry condition settings
    retry_condition_type: RetryConditionType = RetryConditionType.ON_ERROR_TYPE
    retryable_error_types: list[str] = field(default_factory=lambda: [
        "TimeoutError", "ConnectionError", "NetworkError"
    ])
    non_retryable_error_types: list[str] = field(default_factory=lambda: [
        "AuthenticationError", "PermissionError", "ValidationError"
    ])
    retryable_status_codes: list[int] = field(default_factory=lambda: [502, 503, 504])
    non_retryable_status_codes: list[int] = field(default_factory=lambda: [400, 401, 403])
    
    # Performance-based retry
    enable_performance_retry: bool = True
    slow_request_threshold_ms: float = 1000.0
    performance_retry_multiplier: float = 1.5
    
    # Circuit breaker integration
    enable_circuit_breaker: bool = True
    circuit_breaker_name: str | None = None
    
    # Budget management
    enable_retry_budget: bool = True
    retry_budget_window_seconds: float = 60.0
    max_retries_per_window: int = 100
    
    # Advanced metrics
    enable_detailed_metrics: bool = True
    track_retry_reasons: bool = True
    metrics_retention_count: int = 10000
    
    # Custom retry logic
    custom_retry_predicate: Callable | None = None
    custom_backoff_function: Callable | None = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    
    attempt_number: int
    start_time: float
    end_time: float | None = None
    delay_before_attempt: float = 0.0
    error: Exception | None = None
    success: bool = False
    response_time_ms: float | None = None
    
    @property
    def duration_ms(self) -> float | None:
        """Get duration of this attempt."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


@dataclass
class AdvancedRetryMetrics:
    """Enhanced metrics for retry operations."""
    
    # Basic metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_attempts: int = 0
    total_delay_time: float = 0.0
    
    # Performance metrics
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    delay_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    retry_reasons: dict[str, int] = field(default_factory=dict)
    
    # Budget metrics
    retry_budget_used: int = 0
    retry_budget_window_start: float = 0.0
    
    # Adaptive metrics
    adaptive_delays: deque = field(default_factory=lambda: deque(maxlen=100))
    performance_trends: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    def calculate_average_attempts(self) -> float:
        """Calculate average attempts per operation."""
        if self.total_operations == 0:
            return 0.0
        return self.total_attempts / self.total_operations
    
    def calculate_average_delay(self) -> float:
        """Calculate average delay between attempts."""
        if not self.delay_times:
            return 0.0
        return statistics.mean(self.delay_times)
    
    def calculate_retry_budget_usage_rate(self) -> float:
        """Calculate retry budget usage rate."""
        if self.retry_budget_window_start == 0.0:
            return 0.0
        
        window_duration = time.time() - self.retry_budget_window_start
        if window_duration == 0.0:
            return 0.0
        
        return self.retry_budget_used / window_duration


class AdvancedRetryPolicy:
    """Advanced retry policy with adaptive backoff and intelligent retry logic."""
    
    def __init__(self, name: str, config: AdvancedRetryConfig | None = None):
        self.name = name
        self.config = config or AdvancedRetryConfig()
        
        # Metrics tracking
        self._metrics = AdvancedRetryMetrics()
        self._metrics_lock = threading.Lock()
        
        # Performance tracking
        self._recent_response_times = deque(maxlen=self.config.performance_window_size)
        self._performance_stats = {
            'avg_response_time': 0.0,
            'response_time_variance': 0.0,
            'trend_direction': 'stable'  # 'improving', 'degrading', 'stable'
        }
        
        _logger.info(
            "advanced_retry_policy_created",
            name=name,
            backoff_type=self.config.adaptive_backoff_type.value,
            adaptive_enabled=self.config.enable_adaptive_delay
        )
    
    async def execute_with_retry(self, 
                             operation: Callable,
                             *args,
                             operation_name: str | None = None,
                             **kwargs) -> Any:
        """Execute operation with advanced retry logic."""
        operation_name = operation_name or self.name
        start_time = time.time()
        
        # Check retry budget
        if self.config.enable_retry_budget and not self._check_retry_budget():
            _logger.warning("retry_budget_exceeded", operation=operation_name)
            raise RetryableError(f"Retry budget exceeded for operation: {operation_name}")
        
        attempts = []
        last_error = None
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            # Calculate delay before this attempt
            delay = self._calculate_delay(attempt_num, last_error, attempts)
            
            # Wait before attempt (except first attempt)
            if attempt_num > 1 and delay > 0:
                await asyncio.sleep(delay)
            
            # Execute attempt
            attempt_start = time.time()
            attempt = RetryAttempt(
                attempt_number=attempt_num,
                start_time=attempt_start,
                delay_before_attempt=delay
            )
            
            try:
                result = await self._execute_with_timeout(operation, *args, **kwargs)
                
                # Record successful attempt
                attempt.end_time = time.time()
                attempt.success = True
                attempt.response_time_ms = (attempt.end_time - attempt.start_time) * 1000
                
                attempts.append(attempt)
                self._record_success(attempt)
                
                _logger.info(
                    "advanced_retry_success",
                    operation=operation_name,
                    attempt=attempt_num,
                    total_attempts=len(attempts),
                    response_time_ms=attempt.response_time_ms
                )
                
                return result
                
            except Exception as error:
                # Record failed attempt
                attempt.end_time = time.time()
                attempt.error = error
                attempt.response_time_ms = (attempt.end_time - attempt.start_time) * 1000
                
                attempts.append(attempt)
                last_error = error
                
                # Check if we should retry
                retry_decision = self._should_retry(error, attempt_num, attempts)
                
                if retry_decision == RetryDecision.STOP:
                    self._record_failure(attempt, "stop_condition")
                    break
                elif retry_decision == RetryDecision.FAIL_FAST:
                    self._record_failure(attempt, "fail_fast")
                    break
                else:
                    self._record_failure(attempt, "retry")
                    # Continue to next attempt
                    continue
        
        # All attempts failed
        total_duration = (time.time() - start_time) * 1000
        self._record_operation_failure(attempts, total_duration)
        
        _logger.error(
            "advanced_retry_failed",
            operation=operation_name,
            total_attempts=len(attempts),
            total_duration_ms=total_duration,
            final_error=str(last_error)
        )
        
        raise last_error
    
    async def _execute_with_timeout(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with timeout."""
        # Use a reasonable default timeout if not specified
        timeout = getattr(self.config, 'timeout', 30.0)
        
        return await asyncio.wait_for(operation(*args, **kwargs), timeout=timeout)
    
    def _should_retry(self, error: Exception, attempt_num: int, attempts: list[RetryAttempt]) -> RetryDecision:
        """Determine if operation should be retried based on advanced logic."""
        # Check if we've exceeded max attempts
        if attempt_num >= self.config.max_attempts:
            return RetryDecision.STOP
        
        # Check custom retry predicate first
        if self.config.custom_retry_predicate:
            try:
                should_retry = self.config.custom_retry_predicate(error, attempt_num, attempts)
                return RetryDecision.RETRY if should_retry else RetryDecision.STOP
            except Exception as e:
                _logger.error("custom_retry_predicate_failed", error=str(e))
        
        # Apply retry condition logic
        if self.config.retry_condition_type == RetryConditionType.ALWAYS:
            return RetryDecision.RETRY
        
        elif self.config.retry_condition_type == RetryConditionType.ON_ERROR_TYPE:
            error_type = type(error).__name__
            if error_type in self.config.non_retryable_error_types:
                return RetryDecision.FAIL_FAST
            elif error_type in self.config.retryable_error_types:
                return RetryDecision.RETRY
            else:
                return RetryDecision.STOP
        
        elif self.config.retry_condition_type == RetryConditionType.CUSTOM_PREDICATE:
            # Already handled above
            return RetryDecision.STOP
        
        # Default: retry for unknown errors
        return RetryDecision.RETRY
    
    def _calculate_delay(self, attempt_num: int, error: Exception | None, 
                      previous_attempts: list[RetryAttempt]) -> float:
        """Calculate delay before next attempt using adaptive backoff."""
        if self.config.custom_backoff_function:
            try:
                return self.config.custom_backoff_function(attempt_num, error, previous_attempts)
            except Exception as e:
                _logger.error("custom_backoff_function_failed", error=str(e))
        
        base_delay = self.config.base_delay
        
        if self.config.adaptive_backoff_type == AdaptiveBackoffType.EXPONENTIAL:
            delay = base_delay * (self.config.multiplier ** (attempt_num - 1))
        
        elif self.config.adaptive_backoff_type == AdaptiveBackoffType.EXPONENTIAL_WITH_JITTER:
            delay = base_delay * (self.config.multiplier ** (attempt_num - 1))
            if self.config.jitter:
                jitter_range = delay * self.config.jitter_factor
                delay += random.uniform(-jitter_range, jitter_range)
        
        elif self.config.adaptive_backoff_type == AdaptiveBackoffType.LINEAR:
            delay = base_delay + (attempt_num - 1) * self.config.multiplier
        
        elif self.config.adaptive_backoff_type == AdaptiveBackoffType.ADAPTIVE:
            delay = self._calculate_adaptive_delay(attempt_num, previous_attempts)
        
        elif self.config.adaptive_backoff_type == AdaptiveBackoffType.PERFORMANCE_BASED:
            delay = self._calculate_performance_based_delay(attempt_num, previous_attempts)
        
        else:
            delay = base_delay
        
        # Apply bounds
        delay = max(0, min(delay, self.config.max_delay))
        
        # Record delay for metrics
        with self._metrics_lock:
            self._metrics.delay_times.append(delay)
            self._metrics.adaptive_delays.append(delay)
        
        return delay
    
    def _calculate_adaptive_delay(self, attempt_num: int, previous_attempts: list[RetryAttempt]) -> float:
        """Calculate adaptive delay based on historical performance."""
        if len(previous_attempts) < 2:
            return self.config.base_delay
        
        # Analyze previous response times
        response_times = [a.response_time_ms for a in previous_attempts if a.response_time_ms]
        if not response_times:
            return self.config.base_delay
        
        # Calculate trend
        recent_times = response_times[-5:] if len(response_times) >= 5 else response_times
        if len(recent_times) >= 3:
            avg_recent = statistics.mean(recent_times[-3:])
            avg_earlier = statistics.mean(recent_times[:-3]) if len(recent_times) > 3 else avg_recent
            
            if avg_recent > avg_earlier * 1.2:  # Performance degrading
                # Increase delay more aggressively
                multiplier = self.config.multiplier * 1.5
            elif avg_recent < avg_earlier * 0.8:  # Performance improving
                # Can use shorter delays
                multiplier = self.config.multiplier * 0.7
            else:
                multiplier = self.config.multiplier
        else:
            multiplier = self.config.multiplier
        
        delay = self.config.base_delay * (multiplier ** (attempt_num - 1))
        
        # Apply adaptive bounds
        if self.config.enable_adaptive_delay:
            min_delay = self.config.min_adaptive_delay
            max_delay = self.config.max_adaptive_delay
            delay = max(min_delay, min(delay, max_delay))
        
        return delay
    
    def _calculate_performance_based_delay(self, attempt_num: int, previous_attempts: list[RetryAttempt]) -> float:
        """Calculate delay based on performance metrics."""
        if not self.config.enable_performance_retry:
            return self.config.base_delay * (self.config.multiplier ** (attempt_num - 1))
        
        # Check if last attempt was slow
        if previous_attempts:
            last_attempt = previous_attempts[-1]
            if (last_attempt.response_time_ms and 
                last_attempt.response_time_ms > self.config.slow_request_threshold_ms):
                # Last request was slow, increase delay
                multiplier = self.config.multiplier * self.config.performance_retry_multiplier
            else:
                multiplier = self.config.multiplier
        else:
            multiplier = self.config.multiplier
        
        return self.config.base_delay * (multiplier ** (attempt_num - 1))
    
    def _check_retry_budget(self) -> bool:
        """Check if retry budget is available."""
        if not self.config.enable_retry_budget:
            return True
        
        current_time = time.time()
        
        # Reset budget window if needed
        with self._metrics_lock:
            if (current_time - self._metrics.retry_budget_window_start) > self.config.retry_budget_window_seconds:
                self._metrics.retry_budget_used = 0
                self._metrics.retry_budget_window_start = current_time
        
        # Check budget
        return self._metrics.retry_budget_used < self.config.max_retries_per_window
    
    def _record_success(self, attempt: RetryAttempt) -> None:
        """Record successful attempt."""
        with self._metrics_lock:
            self._metrics.total_operations += 1
            self._metrics.successful_operations += 1
            self._metrics.total_attempts += attempt.attempt_number
            
            if attempt.response_time_ms:
                self._metrics.response_times.append(attempt.response_time_ms)
                self._recent_response_times.append(attempt.response_time_ms)
                self._update_performance_stats()
    
    def _record_failure(self, attempt: RetryAttempt, reason: str) -> None:
        """Record failed attempt."""
        with self._metrics_lock:
            self._metrics.total_attempts += attempt.attempt_number
            self._metrics.total_delay_time += attempt.delay_before_attempt
            
            if self.config.track_retry_reasons:
                error_type = type(attempt.error).__name__ if attempt.error else "unknown"
                self._metrics.retry_reasons[error_type] = (
                    self._metrics.retry_reasons.get(error_type, 0) + 1
                )
            
            # Update retry budget
            if self.config.enable_retry_budget:
                self._metrics.retry_budget_used += 1
    
    def _record_operation_failure(self, attempts: list[RetryAttempt], total_duration_ms: float) -> None:
        """Record complete operation failure."""
        with self._metrics_lock:
            self._metrics.total_operations += 1
            self._metrics.failed_operations += 1
            
            # Record all response times
            for attempt in attempts:
                if attempt.response_time_ms:
                    self._metrics.response_times.append(attempt.response_time_ms)
    
    def _update_performance_stats(self) -> None:
        """Update performance statistics for adaptive tuning."""
        if len(self._recent_response_times) < 10:
            return
        
        recent_times = list(self._recent_response_times)[-20:]  # Last 20
        if len(recent_times) < 5:
            return
        
        # Calculate statistics
        avg_time = statistics.mean(recent_times)
        variance = statistics.variance(recent_times) if len(recent_times) > 1 else 0
        
        # Determine trend
        if len(recent_times) >= 10:
            first_half = recent_times[:len(recent_times)//2]
            second_half = recent_times[len(recent_times)//2:]
            
            avg_first = statistics.mean(first_half)
            avg_second = statistics.mean(second_half)
            
            if avg_second > avg_first * 1.1:
                trend = "degrading"
            elif avg_second < avg_first * 0.9:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        self._performance_stats = {
            'avg_response_time': avg_time,
            'response_time_variance': variance,
            'trend_direction': trend
        }
        
        # Store trend for analysis
        self._metrics.performance_trends.append({
            'timestamp': time.time(),
            'avg_time': avg_time,
            'trend': trend
        })
    
    def get_advanced_metrics(self) -> dict[str, Any]:
        """Get comprehensive retry metrics."""
        with self._metrics_lock:
            base_metrics = {
                'name': self.name,
                'total_operations': self._metrics.total_operations,
                'successful_operations': self._metrics.successful_operations,
                'failed_operations': self._metrics.failed_operations,
                'total_attempts': self._metrics.total_attempts,
                'success_rate': self._metrics.calculate_success_rate(),
                'average_attempts': self._metrics.calculate_average_attempts(),
                'total_delay_time': self._metrics.total_delay_time,
                'average_delay': self._metrics.calculate_average_delay(),
                'retry_reasons': self._metrics.retry_reasons.copy(),
            }
            
            # Add performance metrics
            if self._metrics.response_times:
                response_times = list(self._metrics.response_times)
                base_metrics.update({
                    'average_response_time': statistics.mean(response_times),
                    'p95_response_time': self._percentile(response_times, 95),
                    'p99_response_time': self._percentile(response_times, 95),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                })
            
            # Add adaptive metrics
            if self.config.enable_adaptive_delay:
                base_metrics.update({
                    'adaptive_delays': list(self._metrics.adaptive_delays),
                    'performance_stats': self._performance_stats.copy(),
                    'performance_trends': list(self._metrics.performance_trends),
                })
            
            # Add budget metrics
            if self.config.enable_retry_budget:
                base_metrics.update({
                    'retry_budget_used': self._metrics.retry_budget_used,
                    'retry_budget_limit': self.config.max_retries_per_window,
                    'budget_usage_rate': self._metrics.calculate_retry_budget_usage_rate(),
                    'budget_window_start': self._metrics.retry_budget_window_start,
                })
            
            return base_metrics
    
    def update_config(self, new_config: AdvancedRetryConfig) -> None:
        """Update retry policy configuration."""
        self.config = new_config
        _logger.info("advanced_retry_config_updated", name=self.name)
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._metrics_lock:
            self._metrics = AdvancedRetryMetrics()
        
        self._recent_response_times.clear()
        self._performance_stats = {
            'avg_response_time': 0.0,
            'response_time_variance': 0.0,
            'trend_direction': 'stable'
        }
        
        _logger.info("advanced_retry_metrics_reset", name=self.name)
    
    def _percentile(self, data: list[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
