"""Bulkhead pattern for gRPC resilience.

Controls concurrent executions to prevent resource exhaustion
and provides predictable resource usage under high load.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class BulkheadState(Enum):
    """Bulkhead operational states."""
    ACTIVE = "active"
    REJECTING = "rejecting"
    CLOSED = "closed"


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead pattern."""
    
    # Concurrency control
    max_concurrent: int = 100
    max_queue_size: int = 1000
    
    # Timing settings
    queue_timeout_seconds: float = 30.0
    execution_timeout_seconds: float = 60.0
    
    # Metrics
    enable_metrics: bool = True
    metrics_window_size: int = 1000
    
    # Behavior
    reject_when_full: bool = True
    timeout_policy: str = "reject"  # "reject" or "wait"


@dataclass
class BulkheadMetrics:
    """Metrics for bulkhead operations."""
    
    total_requests: int = 0
    accepted_requests: int = 0
    rejected_requests: int = 0
    timeout_requests: int = 0
    completed_requests: int = 0
    
    current_concurrent: int = 0
    peak_concurrent: int = 0
    
    queue_size: int = 0
    peak_queue_size: int = 0
    
    average_execution_time: float = 0.0
    average_queue_time: float = 0.0
    
    # Historical data for trends
    execution_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    queue_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def update_execution_metrics(self, execution_time: float, queue_time: float) -> None:
        """Update execution metrics with new data point."""
        self.execution_history.append(execution_time)
        self.queue_history.append(queue_time)
        
        # Calculate rolling averages
        if self.execution_history:
            self.average_execution_time = sum(self.execution_history) / len(self.execution_history)
        
        if self.queue_history:
            self.average_queue_time = sum(self.queue_history) / len(self.queue_history)
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.completed_requests / self.total_requests) * 100


class BulkheadRejectedError(Exception):
    """Raised when bulkhead rejects a request due to capacity limits."""
    
    def __init__(self, reason: str, current_load: int, max_capacity: int):
        self.reason = reason
        self.current_load = current_load
        self.max_capacity = max_capacity
        super().__init__(f"Bulkhead rejected: {reason} (current: {current_load}, max: {max_capacity})")


class BulkheadTimeoutError(Exception):
    """Raised when bulkhead operation times out."""
    
    def __init__(self, timeout_type: str, timeout_seconds: float):
        self.timeout_type = timeout_type
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Bulkhead timeout: {timeout_type} after {timeout_seconds}s")


class GrpcBulkhead:
    """Bulkhead pattern implementation for gRPC services."""
    
    def __init__(self, config: BulkheadConfig | None = None):
        self.config = config or BulkheadConfig()
        self.metrics = BulkheadMetrics()
        self.state = BulkheadState.ACTIVE
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._current_concurrent = 0
        self._concurrent_lock = asyncio.Lock()
        
        # Queue management
        self._queue = asyncio.Queue(maxsize=self.config.max_queue_size)
        self._queue_size = 0
        self._queue_lock = asyncio.Lock()
        
        # Background tasks
        self._background_tasks: list[asyncio.Task] = []
        self._running = False
        
        _logger.info(
            "grpc_bulkhead_initialized",
            max_concurrent=self.config.max_concurrent,
            max_queue_size=self.config.max_queue_size,
            timeout_policy=self.config.timeout_policy
        )
    
    async def execute(self, 
                   func: Callable,
                   *args,
                   timeout: float | None = None,
                   **kwargs) -> Any:
        """Execute function with bulkhead protection."""
        if self.state == BulkheadState.CLOSED:
            raise BulkheadRejectedError("Bulkhead is closed", 0, 0)
        
        start_time = time.time()
        execution_timeout = timeout or self.config.execution_timeout_seconds
        
        # Update metrics
        self.metrics.total_requests += 1
        
        # Try to acquire semaphore or queue
        try:
            if self.config.timeout_policy == "reject":
                # Fast rejection policy
                if self._queue.full() and self._current_concurrent >= self.config.max_concurrent:
                    self.metrics.rejected_requests += 1
                    raise BulkheadRejectedError(
                        "Capacity exceeded", 
                        self._current_concurrent, 
                        self.config.max_concurrent
                    )
                
                # Queue the request
                queue_start = time.time()
                await self._queue.put((func, args, kwargs, queue_start))
                
                # Update queue metrics
                async with self._queue_lock:
                    self._queue_size = self._queue.qsize()
                    self.metrics.queue_size = self._queue_size
                    self.metrics.peak_queue_size = max(self.metrics.peak_queue_size, self._queue_size)
                
                # Wait for execution
                result = await asyncio.wait_for(
                    self._execute_from_queue(),
                    timeout=self.config.queue_timeout_seconds
                )
                
            else:
                # Wait policy
                queue_start = time.time()
                await asyncio.wait_for(
                    self._queue.put((func, args, kwargs, queue_start)),
                    timeout=self.config.queue_timeout_seconds
                )
                
                result = await asyncio.wait_for(
                    self._execute_from_queue(),
                    timeout=execution_timeout
                )
            
            # Calculate queue time
            queue_time = time.time() - queue_start
            self.metrics.update_execution_metrics(0.0, queue_time)  # Will be updated after execution
            
            return result
            
        except TimeoutError:
            self.metrics.timeout_requests += 1
            timeout_type = "queue" if self.config.timeout_policy == "reject" else "execution"
            raise BulkheadTimeoutError(timeout_type, execution_timeout)
        
        except Exception as e:
            self.metrics.rejected_requests += 1
            _logger.error("bulkhead_execution_failed", error=str(e))
            raise
    
    async def _execute_from_queue(self) -> Any:
        """Execute function from queue with semaphore protection."""
        func, args, kwargs, queue_start = await self._queue.get()
        
        # Update queue size
        async with self._queue_lock:
            self._queue_size = self._queue.qsize()
        
        # Acquire semaphore
        async with self._semaphore:
            # Update concurrent metrics
            async with self._concurrent_lock:
                self._current_concurrent += 1
                self.metrics.current_concurrent = self._current_concurrent
                self.metrics.peak_concurrent = max(
                    self.metrics.peak_concurrent, 
                    self._current_concurrent
                )
            
            try:
                # Execute the function
                execution_start = time.time()
                
                # Calculate actual queue time
                queue_time = execution_start - queue_start
                
                result = await func(*args, **kwargs)
                
                # Update execution metrics
                execution_time = time.time() - execution_start
                self.metrics.update_execution_metrics(execution_time, queue_time)
                self.metrics.completed_requests += 1
                self.metrics.accepted_requests += 1
                
                return result
                
            finally:
                # Update concurrent metrics
                async with self._concurrent_lock:
                    self._current_concurrent -= 1
                    self.metrics.current_concurrent = self._current_concurrent
    
    async def get_status(self) -> dict[str, Any]:
        """Get current bulkhead status."""
        async with self._concurrent_lock:
            current_concurrent = self._current_concurrent
        
        async with self._queue_lock:
            queue_size = self._queue_size
        
        return {
            'state': self.state.value,
            'current_concurrent': current_concurrent,
            'max_concurrent': self.config.max_concurrent,
            'queue_size': queue_size,
            'max_queue_size': self.config.max_queue_size,
            'utilization_percent': (current_concurrent / self.config.max_concurrent) * 100,
            'queue_utilization_percent': (queue_size / self.config.max_queue_size) * 100
        }
    
    async def get_metrics(self) -> dict[str, Any]:
        """Get bulkhead metrics."""
        async with self._concurrent_lock:
            current_concurrent = self._current_concurrent
        
        async with self._queue_lock:
            queue_size = self._queue_size
        
        base_metrics = {
            'total_requests': self.metrics.total_requests,
            'accepted_requests': self.metrics.accepted_requests,
            'rejected_requests': self.metrics.rejected_requests,
            'timeout_requests': self.metrics.timeout_requests,
            'completed_requests': self.metrics.completed_requests,
            'success_rate': self.metrics.get_success_rate(),
            'current_concurrent': current_concurrent,
            'peak_concurrent': self.metrics.peak_concurrent,
            'current_queue_size': queue_size,
            'peak_queue_size': self.metrics.peak_queue_size,
            'average_execution_time': self.metrics.average_execution_time,
            'average_queue_time': self.metrics.average_queue_time,
        }
        
        # Add historical statistics if enabled
        if self.config.enable_metrics and self.metrics.execution_history:
            recent_executions = list(self.metrics.execution_history)[-100:]  # Last 100
            recent_queues = list(self.metrics.queue_history)[-100:]  # Last 100
            
            if recent_executions:
                base_metrics.update({
                    'p95_execution_time': self._percentile(recent_executions, 95),
                    'p99_execution_time': self._percentile(recent_executions, 99),
                    'min_execution_time': min(recent_executions),
                    'max_execution_time': max(recent_executions),
                })
            
            if recent_queues:
                base_metrics.update({
                    'p95_queue_time': self._percentile(recent_queues, 95),
                    'p99_queue_time': self._percentile(recent_queues, 99),
                    'min_queue_time': min(recent_queues),
                    'max_queue_time': max(recent_queues),
                })
        
        return base_metrics
    
    def update_config(self, new_config: BulkheadConfig) -> None:
        """Update bulkhead configuration."""
        old_max_concurrent = self.config.max_concurrent
        old_max_queue = self.config.max_queue_size
        
        self.config = new_config
        
        # Update semaphore if max_concurrent changed
        if old_max_concurrent != new_config.max_concurrent:
            # This is tricky - we need to create a new semaphore
            # In practice, this would require careful coordination
            _logger.warning(
                "bulkhead_concurrency_changed",
                old=old_max_concurrent,
                new=new_config.max_concurrent,
                note="Semaphore update requires restart"
            )
        
        # Update queue size if changed
        if old_max_queue != new_config.max_queue_size:
            # Create new queue and migrate existing items
            old_queue = self._queue
            self._queue = asyncio.Queue(maxsize=new_config.max_queue_size)
            
            # Migrate existing items (simplified)
            try:
                while not old_queue.empty():
                    item = old_queue.get_nowait()
                    if not self._queue.full():
                        self._queue.put_nowait(item)
            except asyncio.QueueFull:
                _logger.warning("bulkhead_queue_migration_items_lost")
        
        _logger.info("bulkhead_config_updated", config=new_config)
    
    def close(self) -> None:
        """Close bulkhead and reject new requests."""
        self.state = BulkheadState.CLOSED
        
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        _logger.info("grpc_bulkhead_closed")
    
    def reopen(self) -> None:
        """Reopen bulkhead for new requests."""
        self.state = BulkheadState.ACTIVE
        _logger.info("grpc_bulkhead_reopened")
    
    def reset_metrics(self) -> None:
        """Reset bulkhead metrics."""
        self.metrics = BulkheadMetrics()
        _logger.info("grpc_bulkhead_metrics_reset")
    
    def _percentile(self, data: list[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        
        return sorted_data[index]
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()
