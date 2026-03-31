"""Enhanced gRPC circuit breaker with dynamic configuration and advanced metrics.

Provides intelligent circuit breaking with adaptive thresholds,
performance-based tuning, and comprehensive monitoring integration.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from typing import Any

from mindflow_backend.grpc.resilience.circuit_breaker import (
    CircuitBreakerOpenError,
    CircuitState,
)
from mindflow_backend.infra.logging import get_logger

from .circuit_breaker.config import AdaptiveThresholdType, EnhancedCircuitBreakerConfig
from .circuit_breaker.metrics import CircuitBreakerMetrics

_logger = get_logger(__name__)


class EnhancedGrpcCircuitBreaker:
    """Enhanced circuit breaker with adaptive thresholds and advanced metrics."""
    
    def __init__(self, name: str, config: EnhancedCircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or EnhancedCircuitBreakerConfig()
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._last_success_time: float | None = None
        self._half_open_calls = 0
        
        # Enhanced metrics
        self._metrics = CircuitBreakerMetrics()
        
        # Dynamic configuration
        self._config_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        
        # Background tasks
        self._background_tasks: list[asyncio.Task] = []
        self._running = False
        
        # Performance tracking
        self._response_times = deque(maxlen=self.config.performance_window_size)
        self._call_history = deque(maxlen=self.config.adaptive_window_size)
        
        _logger.info(
            "enhanced_circuit_breaker_created",
            name=name,
            adaptive_type=self.config.adaptive_threshold_type.value,
            dynamic_config=self.config.enable_dynamic_config
        )
        
        # Start background tasks if enabled
        if self.config.enable_dynamic_config:
            self._start_background_tasks()
    
    async def call(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation with enhanced circuit breaker protection."""
        start_time = time.time()
        
        async with self._config_lock:
            if not self._should_attempt_call():
                self._record_call_attempt(False, 0.0, CircuitBreakerOpenError())
                raise CircuitBreakerOpenError(f"Enhanced circuit breaker '{self.name}' is OPEN")
        
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
            
        except TimeoutError as exc:
            duration = time.time() - start_time
            self._record_failure(duration, exc)
            raise
        
        except Exception as exc:
            duration = time.time() - start_time
            self._record_failure(duration, exc)
            raise
    
    def _should_attempt_call(self) -> bool:
        """Enhanced logic for determining if call should be attempted."""
        if self._state == CircuitState.CLOSED:
            return True
        
        elif self._state == CircuitState.OPEN:
            # Check recovery timeout
            if (self._last_failure_time and 
                time.time() - self._last_failure_time >= self.config.recovery_timeout):
                self._transition_to_half_open()
                return True
            return False
        
        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self._half_open_calls < self.config.max_half_open_calls
        
        return False
    
    def _record_success(self, duration: float) -> None:
        """Record successful operation with enhanced metrics."""
        with self._metrics_lock:
            self._metrics.total_calls += 1
            self._metrics.successful_calls += 1
            self._metrics.response_times.append(duration)
            self._call_history.append(1)  # 1 = success
            
            self._last_success_time = time.time()
            
            # Update state-specific logic
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self._failure_count = 0
            
            # Check adaptive thresholds
            if self.config.auto_tune_thresholds:
                self._check_adaptive_thresholds()
        
        # Trigger callbacks
        if self.config.enable_event_callbacks:
            self._trigger_state_change_callbacks('success', {
                'duration': duration,
                'state': self._state.value
            })
        
        _logger.debug(
            "enhanced_circuit_breaker_success",
            name=self.name,
            state=self._state.value,
            duration=duration,
            current_threshold=self._metrics.current_threshold
        )
    
    def _record_failure(self, duration: float, error: Exception) -> None:
        """Record failed operation with enhanced metrics."""
        error_type = type(error).__name__
        
        with self._metrics_lock:
            self._metrics.total_calls += 1
            self._metrics.failed_calls += 1
            self._metrics.response_times.append(-duration)  # Negative = failure
            self._call_history.append(0)  # 0 = failure
            
            # Track failure reasons
            self._metrics.failure_reasons[error_type] = (
                self._metrics.failure_reasons.get(error_type, 0) + 1
            )
            
            self._last_failure_time = time.time()
            
            # Update state-specific logic
            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                current_threshold = self._get_adaptive_threshold()
                if self._failure_count >= current_threshold:
                    self._transition_to_open()
            
            elif self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open state opens circuit again
                self._transition_to_open()
            
            # Check adaptive thresholds
            if self.config.auto_tune_thresholds:
                self._check_adaptive_thresholds()
        
        # Trigger callbacks
        if self.config.enable_event_callbacks:
            self._trigger_state_change_callbacks('failure', {
                'duration': duration,
                'error_type': error_type,
                'state': self._state.value
            })
        
        _logger.warning(
            "enhanced_circuit_breaker_failure",
            name=self.name,
            state=self._state.value,
            duration=duration,
            error_type=error_type,
            current_threshold=self._metrics.current_threshold
        )
    
    def _get_adaptive_threshold(self) -> int:
        """Get adaptive failure threshold based on strategy."""
        if self.config.adaptive_threshold_type == AdaptiveThresholdType.FIXED:
            return self.config.failure_threshold
        
        elif self.config.adaptive_threshold_type == AdaptiveThresholdType.PERCENTILE_BASED:
            return self._calculate_percentile_threshold()
        
        elif self.config.adaptive_threshold_type == AdaptiveThresholdType.RATE_BASED:
            return self._calculate_rate_threshold()
        
        elif self.config.adaptive_threshold_type == AdaptiveThresholdType.PERFORMANCE_BASED:
            return self._calculate_performance_threshold()
        
        return self.config.failure_threshold
    
    def _calculate_percentile_threshold(self) -> int:
        """Calculate threshold based on failure rate percentile."""
        if len(self._call_history) < self.config.adaptive_window_size:
            return self.config.failure_threshold
        
        # Calculate recent failure rate
        recent_calls = list(self._call_history)[-self.config.adaptive_window_size:]
        failure_rate = 1.0 - (sum(recent_calls) / len(recent_calls))
        
        # Adapt threshold based on failure rate
        if failure_rate > 0.8:  # >80% failure rate
            return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)
        elif failure_rate > 0.5:  # >50% failure rate
            return self.config.failure_threshold
        else:  # <50% failure rate
            return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)
    
    def _calculate_rate_threshold(self) -> int:
        """Calculate threshold based on failure rate."""
        failure_rate = self._metrics.calculate_failure_rate(self.config.rate_window_size)
        
        if failure_rate > self.config.failure_rate_threshold:
            return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)
        elif failure_rate > self.config.failure_rate_threshold / 2:
            return self.config.failure_threshold
        else:
            return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)
    
    def _calculate_performance_threshold(self) -> int:
        """Calculate threshold based on performance metrics."""
        avg_response_time = self._metrics.calculate_average_response_time(self.config.performance_window_size)
        
        if avg_response_time > self.config.performance_threshold_ms:
            # Performance is degraded, lower threshold to be more sensitive
            return max(self.config.min_failure_threshold, self.config.failure_threshold // 2)
        else:
            # Performance is good, can be more lenient
            return min(self.config.max_failure_threshold, self.config.failure_threshold * 2)
    
    def _check_adaptive_thresholds(self) -> None:
        """Check and update adaptive thresholds."""
        new_threshold = self._get_adaptive_threshold()
        
        if new_threshold != self._metrics.current_threshold:
            old_threshold = self._metrics.current_threshold
            self._metrics.current_threshold = new_threshold
            self._metrics.threshold_history.append(new_threshold)
            
            _logger.info(
                "adaptive_threshold_updated",
                name=self.name,
                old_threshold=old_threshold,
                new_threshold=new_threshold,
                strategy=self.config.adaptive_threshold_type.value
            )
    
    def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state with enhanced tracking."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._state_change_time = time.time()
        
        # Record state transition
        transition_data = {
            'from_state': old_state.value,
            'to_state': CircuitState.OPEN.value,
            'timestamp': time.time(),
            'failure_count': self._failure_count,
            'threshold': self._metrics.current_threshold,
            'reason': 'failure_threshold_exceeded'
        }
        
        with self._metrics_lock:
            self._metrics.state_transitions.append(transition_data)
            self._metrics.state_durations[old_state.value] = (
                self._metrics.state_durations.get(old_state.value, 0.0) + 
                (time.time() - self._metrics.last_state_change)
            )
            self._metrics.last_state_change = time.time()
        
        # Trigger callbacks
        if self.config.enable_event_callbacks:
            self._trigger_state_change_callbacks('state_change', transition_data)
        
        _logger.warning(
            "enhanced_circuit_breaker_opened",
            name=self.name,
            previous_state=old_state.value,
            failure_count=self._failure_count,
            threshold=self._metrics.current_threshold
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._state_change_time = time.time()
        self._success_count = 0
        self._half_open_calls = 0
        
        # Record state transition
        transition_data = {
            'from_state': old_state.value,
            'to_state': CircuitState.HALF_OPEN.value,
            'timestamp': time.time(),
            'reason': 'recovery_timeout'
        }
        
        with self._metrics_lock:
            self._metrics.state_transitions.append(transition_data)
            self._metrics.state_durations[old_state.value] = (
                self._metrics.state_durations.get(old_state.value, 0.0) + 
                (time.time() - self._metrics.last_state_change)
            )
            self._metrics.last_state_change = time.time()
        
        # Trigger callbacks
        if self.config.enable_event_callbacks:
            self._trigger_state_change_callbacks('state_change', transition_data)
        
        _logger.info(
            "enhanced_circuit_breaker_half_open",
            name=self.name,
            previous_state=old_state.value
        )
    
    def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._state_change_time = time.time()
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        
        # Record state transition
        transition_data = {
            'from_state': old_state.value,
            'to_state': CircuitState.CLOSED.value,
            'timestamp': time.time(),
            'success_count': self._success_count,
            'reason': 'recovery_successful'
        }
        
        with self._metrics_lock:
            self._metrics.state_transitions.append(transition_data)
            self._metrics.state_durations[old_state.value] = (
                self._metrics.state_durations.get(old_state.value, 0.0) + 
                (time.time() - self._metrics.last_state_change)
            )
            self._metrics.last_state_change = time.time()
        
        # Trigger callbacks
        if self.config.enable_event_callbacks:
            self._trigger_state_change_callbacks('state_change', transition_data)
        
        _logger.info(
            "enhanced_circuit_breaker_closed",
            name=self.name,
            previous_state=old_state.value,
            success_count=self._success_count
        )
    
    def _trigger_state_change_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """Trigger state change callbacks."""
        for callback in self.config.state_change_callbacks:
            try:
                callback(self.name, event_type, data)
            except Exception as e:
                _logger.error("state_change_callback_failed", error=str(e))
    
    def _start_background_tasks(self) -> None:
        """Start background tasks for dynamic configuration."""
        if self._running:
            return
        
        self._running = True
        
        # Configuration update task
        if self.config.enable_dynamic_config:
            task = asyncio.create_task(self._config_update_loop())
            self._background_tasks.append(task)
    
    async def _config_update_loop(self) -> None:
        """Background loop for dynamic configuration updates."""
        while self._running:
            try:
                await asyncio.sleep(self.config.config_update_interval_seconds)
                
                if self.config.auto_tune_thresholds:
                    self._check_adaptive_thresholds()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                _logger.error("config_update_loop_error", error=str(e))
    
    def get_enhanced_metrics(self) -> dict[str, Any]:
        """Get comprehensive circuit breaker metrics."""
        with self._metrics_lock:
            base_metrics = {
                'name': self.name,
                'state': self._state.value,
                'current_threshold': self._metrics.current_threshold,
                'total_calls': self._metrics.total_calls,
                'successful_calls': self._metrics.successful_calls,
                'failed_calls': self._metrics.failed_calls,
                'timeout_calls': self._metrics.timeout_calls,
                'success_rate': self._metrics.calculate_success_rate(),
                'failure_rate': self._metrics.calculate_failure_rate(),
                'average_response_time': self._metrics.calculate_average_response_time(),
                'p95_response_time': self._metrics.get_percentile_response_time(95),
                'p99_response_time': self._metrics.get_percentile_response_time(99),
                'failure_reasons': self._metrics.failure_reasons.copy(),
                'state_transitions': self._metrics.state_transitions.copy(),
                'state_durations': self._metrics.state_durations.copy(),
                'last_state_change': self._metrics.last_state_change,
            }
            
            # Add adaptive metrics
            if self.config.adaptive_threshold_type != AdaptiveThresholdType.FIXED:
                base_metrics.update({
                    'adaptive_type': self.config.adaptive_threshold_type.value,
                    'min_threshold': self.config.min_failure_threshold,
                    'max_threshold': self.config.max_failure_threshold,
                    'threshold_history': list(self._metrics.threshold_history),
                })
            
            # Add performance metrics
            if self._response_times:
                base_metrics.update({
                    'performance_threshold_ms': self.config.performance_threshold_ms,
                    'performance_window_size': self.config.performance_window_size,
                    'current_performance': self._metrics.calculate_average_response_time(self.config.performance_window_size),
                })
            
            return base_metrics
    
    def update_config(self, new_config: EnhancedCircuitBreakerConfig) -> None:
        """Update circuit breaker configuration dynamically."""
        with self._config_lock:
            old_config = self.config
            self.config = new_config
            
            # Restart background tasks if needed
            if new_config.enable_dynamic_config != old_config.enable_dynamic_config:
                if new_config.enable_dynamic_config:
                    self._start_background_tasks()
                else:
                    self._stop_background_tasks()
        
        _logger.info("enhanced_circuit_breaker_config_updated", name=self.name)
    
    def add_state_change_callback(self, callback: Callable) -> None:
        """Add callback for state change events."""
        if callback not in self.config.state_change_callbacks:
            self.config.state_change_callbacks.append(callback)
            _logger.info("state_change_callback_added", name=self.name)
    
    def remove_state_change_callback(self, callback: Callable) -> None:
        """Remove state change callback."""
        if callback in self.config.state_change_callbacks:
            self.config.state_change_callbacks.remove(callback)
            _logger.info("state_change_callback_removed", name=self.name)
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        with self._metrics_lock:
            self._metrics = CircuitBreakerMetrics()
        
        _logger.info("enhanced_circuit_breaker_metrics_reset", name=self.name)
    
    def _stop_background_tasks(self) -> None:
        """Stop background tasks."""
        self._running = False
        
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        self._background_tasks = []
        _logger.info("enhanced_circuit_breaker_background_tasks_stopped", name=self.name)
    
    def __del__(self):
        """Cleanup on deletion."""
        self._stop_background_tasks()


# Export public classes
__all__ = [
    "AdaptiveThresholdType",
    "EnhancedCircuitBreakerConfig", 
    "CircuitBreakerMetrics",
    "EnhancedGrpcCircuitBreaker",
]
