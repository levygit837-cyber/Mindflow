"""Timeout management for gRPC operations.

Provides sophisticated timeout handling including per-operation timeouts,
deadline propagation, and adaptive timeout strategies.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, Union
from dataclasses import dataclass, field

import grpc
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class TimeoutConfig:
    """Configuration for timeout management."""
    default_timeout: float = 30.0           # Default timeout in seconds
    short_timeout: float = 5.0              # Short operations timeout
    long_timeout: float = 300.0             # Long operations timeout
    streaming_timeout: float = 600.0        # Streaming operations timeout
    
    # Per-operation timeouts
    operation_timeouts: Dict[str, float] = field(default_factory=dict)
    
    # Adaptive timeout settings
    enable_adaptive: bool = False
    min_timeout: float = 1.0
    max_timeout: float = 600.0
    adjustment_factor: float = 1.5
    
    # Deadline settings
    enable_deadline_propagation: bool = True
    deadline_buffer_seconds: float = 5.0
    
    # Timeout escalation
    enable_escalation: bool = True
    escalation_threshold: float = 0.8        # Escalate when 80% of timeout used


class TimeoutError(Exception):
    """Raised when operation times out."""
    def __init__(self, operation: str, timeout: float, elapsed: float):
        self.operation = operation
        self.timeout = timeout
        self.elapsed = elapsed
        super().__init__(f"Operation '{operation}' timed out after {elapsed:.2f}s (limit: {timeout:.2f}s)")


class TimeoutManager:
    """Advanced timeout manager for gRPC operations."""
    
    def __init__(self, config: TimeoutConfig | None = None):
        self.config = config or TimeoutConfig()
        self._operation_history: Dict[str, List[Dict[str, Any]]] = {}
        self._adaptive_timeouts: Dict[str, float] = {}
    
    @asynccontextmanager
    async def timeout_context(self, operation: str, timeout: float | None = None):
        """Context manager for operation timeout."""
        start_time = time.time()
        effective_timeout = timeout or self.get_timeout_for_operation(operation)
        
        try:
            # Create timeout task
            timeout_task = asyncio.create_task(
                asyncio.sleep(effective_timeout),
                name=f"timeout_{operation}"
            )
            
            # Record operation start
            self._record_operation_start(operation, effective_timeout)
            
            yield effective_timeout
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            self._record_operation_timeout(operation, effective_timeout, elapsed)
            raise TimeoutError(operation, effective_timeout, elapsed)
        finally:
            # Cancel timeout task if still running
            if 'timeout_task' in locals():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass
            
            # Record operation completion
            elapsed = time.time() - start_time
            self._record_operation_completion(operation, effective_timeout, elapsed)
    
    async def execute_with_timeout(self, operation: Callable, operation_name: str, 
                                timeout: float | None = None, *args, **kwargs) -> Any:
        """Execute operation with timeout protection."""
        async with self.timeout_context(operation_name, timeout) as effective_timeout:
            try:
                # Execute with asyncio.wait_for
                result = await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=effective_timeout
                )
                return result
            except asyncio.TimeoutError:
                elapsed = time.time() - time.time()
                raise TimeoutError(operation_name, effective_timeout, elapsed)
    
    def get_timeout_for_operation(self, operation: str) -> float:
        """Get appropriate timeout for operation."""
        # Check per-operation timeout
        if operation in self.config.operation_timeouts:
            return self.config.operation_timeouts[operation]
        
        # Check adaptive timeout
        if self.config.enable_adaptive and operation in self._adaptive_timeouts:
            return self._adaptive_timeouts[operation]
        
        # Determine timeout based on operation type
        if self._is_streaming_operation(operation):
            return self.config.streaming_timeout
        elif self._is_long_operation(operation):
            return self.config.long_timeout
        elif self._is_short_operation(operation):
            return self.config.short_timeout
        else:
            return self.config.default_timeout
    
    def create_grpc_options(self, operation: str, timeout: float | None = None) -> Dict[str, Any]:
        """Create gRPC options with timeout."""
        effective_timeout = timeout or self.get_timeout_for_operation(operation)
        
        options = {
            'timeout': effective_timeout,
        }
        
        # Add deadline if enabled
        if self.config.enable_deadline_propagation:
            deadline = time.time() + effective_timeout - self.config.deadline_buffer_seconds
            options['deadline'] = deadline
        
        return options
    
    def update_adaptive_timeout(self, operation: str, success: bool, duration: float):
        """Update adaptive timeout based on operation performance."""
        if not self.config.enable_adaptive:
            return
        
        history = self._operation_history.get(operation, [])
        if not history:
            return
        
        # Calculate average duration for recent successful operations
        recent_successful = [
            h for h in history[-10:]  # Last 10 operations
            if h['success'] and not h.get('timeout')
        ]
        
        if len(recent_successful) < 3:  # Need at least 3 samples
            return
        
        avg_duration = sum(h['duration'] for h in recent_successful) / len(recent_successful)
        
        # Calculate new adaptive timeout
        if success:
            # Successful operation: adjust timeout to be slightly above average
            new_timeout = min(
                avg_duration * self.config.adjustment_factor,
                self.config.max_timeout
            )
        else:
            # Failed operation: increase timeout more aggressively
            new_timeout = min(
                avg_duration * (self.config.adjustment_factor * 2),
                self.config.max_timeout
            )
        
        # Ensure timeout is within bounds
        new_timeout = max(self.config.min_timeout, new_timeout)
        
        # Update adaptive timeout
        old_timeout = self._adaptive_timeouts.get(operation, self.config.default_timeout)
        self._adaptive_timeouts[operation] = new_timeout
        
        _logger.debug(
            "adaptive_timeout_updated",
            operation=operation,
            old_timeout=old_timeout,
            new_timeout=new_timeout,
            success=success,
            avg_duration=avg_duration
        )
    
    def check_timeout_escalation(self, operation: str, elapsed: float, timeout: float) -> bool:
        """Check if timeout should be escalated based on usage."""
        if not self.config.enable_escalation:
            return False
        
        usage_ratio = elapsed / timeout
        return usage_ratio >= self.config.escalation_threshold
    
    def _record_operation_start(self, operation: str, timeout: float):
        """Record operation start."""
        if operation not in self._operation_history:
            self._operation_history[operation] = []
        
        self._operation_history[operation].append({
            'start_time': time.time(),
            'timeout': timeout,
            'success': None,
            'duration': None,
            'timeout': None,
        })
    
    def _record_operation_completion(self, operation: str, timeout: float, duration: float):
        """Record successful operation completion."""
        history = self._operation_history.get(operation, [])
        if history:
            last_record = history[-1]
            last_record.update({
                'success': True,
                'duration': duration,
                'timeout': False,
            })
        
        # Update adaptive timeout
        self.update_adaptive_timeout(operation, True, duration)
    
    def _record_operation_timeout(self, operation: str, timeout: float, elapsed: float):
        """Record operation timeout."""
        history = self._operation_history.get(operation, [])
        if history:
            last_record = history[-1]
            last_record.update({
                'success': False,
                'duration': elapsed,
                'timeout': True,
            })
        
        # Update adaptive timeout
        self.update_adaptive_timeout(operation, False, elapsed)
    
    def _is_streaming_operation(self, operation: str) -> bool:
        """Check if operation is streaming."""
        streaming_keywords = ['stream', 'chat', 'subscribe', 'watch']
        return any(keyword in operation.lower() for keyword in streaming_keywords)
    
    def _is_long_operation(self, operation: str) -> bool:
        """Check if operation is long-running."""
        long_keywords = ['process', 'analyze', 'compile', 'train', 'index']
        return any(keyword in operation.lower() for keyword in long_keywords)
    
    def _is_short_operation(self, operation: str) -> bool:
        """Check if operation is short-running."""
        short_keywords = ['ping', 'health', 'status', 'echo', 'validate']
        return any(keyword in operation.lower() for keyword in short_keywords)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get timeout statistics."""
        stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'timeout_operations': 0,
            'average_duration': 0.0,
            'operation_stats': {},
            'adaptive_timeouts': dict(self._adaptive_timeouts),
        }
        
        total_duration = 0.0
        total_operations = 0
        successful_operations = 0
        timeout_operations = 0
        
        for operation, history in self._operation_history.items():
            if not history:
                continue
            
            operation_stats = {
                'total': len(history),
                'successful': 0,
                'timeouts': 0,
                'average_duration': 0.0,
                'timeout_rate': 0.0,
            }
            
            operation_duration = 0.0
            for record in history:
                if record['success'] is not None:
                    total_operations += 1
                    operation_stats['total'] += 1
                    
                    if record['success']:
                        successful_operations += 1
                        operation_stats['successful'] += 1
                        operation_duration += record['duration']
                    else:
                        timeout_operations += 1
                        operation_stats['timeouts'] += 1
            
            if operation_stats['successful'] > 0:
                operation_stats['average_duration'] = operation_duration / operation_stats['successful']
                operation_stats['timeout_rate'] = operation_stats['timeouts'] / operation_stats['total']
            
            stats['operation_stats'][operation] = operation_stats
            total_duration += operation_duration
        
        stats.update({
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'timeout_operations': timeout_operations,
            'average_duration': total_duration / max(successful_operations, 1),
            'timeout_rate': timeout_operations / max(total_operations, 1),
        })
        
        return stats
    
    def reset_statistics(self):
        """Reset all statistics."""
        self._operation_history.clear()
        self._adaptive_timeouts.clear()


# Global timeout manager instance
_global_timeout_manager = TimeoutManager()


def get_timeout_manager() -> TimeoutManager:
    """Get global timeout manager instance."""
    return _global_timeout_manager


def with_timeout(operation_name: str, timeout: float | None = None):
    """Decorator for adding timeout to functions."""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            timeout_mgr = get_timeout_manager()
            return await timeout_mgr.execute_with_timeout(
                func, operation_name, timeout, *args, **kwargs
            )
        
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we'll need to run them in an executor
            async def async_func():
                return func(*args, **kwargs)
            
            timeout_mgr = get_timeout_manager()
            return asyncio.run(timeout_mgr.execute_with_timeout(
                async_func, operation_name, timeout
            ))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Predefined timeout configurations
FAST_TIMEOUT_CONFIG = TimeoutConfig(
    default_timeout=5.0,
    short_timeout=1.0,
    long_timeout=30.0,
    streaming_timeout=120.0,
    enable_adaptive=True,
    min_timeout=0.5,
    max_timeout=60.0
)

SLOW_TIMEOUT_CONFIG = TimeoutConfig(
    default_timeout=120.0,
    short_timeout=10.0,
    long_timeout=600.0,
    streaming_timeout=1800.0,
    enable_adaptive=True,
    min_timeout=5.0,
    max_timeout=3600.0
)

ADAPTIVE_TIMEOUT_CONFIG = TimeoutConfig(
    default_timeout=30.0,
    enable_adaptive=True,
    adjustment_factor=2.0,
    enable_escalation=True,
    escalation_threshold=0.7
)
