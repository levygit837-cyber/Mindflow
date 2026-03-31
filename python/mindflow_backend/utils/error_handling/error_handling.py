"""Error handling utilities for MindFlow.

Provides helper functions, decorators, and utilities for consistent
error handling across the system.
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from mindflow_backend.exceptions import MindFlowError
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)
T = TypeVar('T')


def handle_errors(
    *,
    error_type: type[Exception] = Exception,
    default_return: Any = None,
    log_error: bool = True,
    reraise: bool = False,
    error_message: str | None = None,
) -> Callable:
    """Decorator for consistent error handling."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return func(*args, **kwargs)
            except error_type as exc:
                if log_error:
                    _logger.error(
                        "function_error",
                        function=func.__name__,
                        error=str(exc),
                        error_type=exc.__class__.__name__,
                    )
                
                if reraise:
                    if error_message:
                        raise type(exc)(error_message) from exc
                    raise
                
                return default_return
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T | Any:
            try:
                return await func(*args, **kwargs)
            except error_type as exc:
                if log_error:
                    _logger.error(
                        "async_function_error",
                        function=func.__name__,
                        error=str(exc),
                        error_type=exc.__class__.__name__,
                    )
                
                if reraise:
                    if error_message:
                        raise type(exc)(error_message) from exc
                    raise
                
                return default_return
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def retry_on_error(
    *,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_attempts: bool = True,
) -> Callable:
    """Decorator for retrying functions on specific exceptions."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise
                        if log_attempts:
                            _logger.error(
                                "retry_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    if log_attempts:
                        _logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(exc),
                        )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception  # type: ignore
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        # Last attempt, re-raise
                        if log_attempts:
                            _logger.error(
                                "async_retry_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    if log_attempts:
                        _logger.warning(
                            "async_retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(exc),
                        )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
            
            # This should never be reached, but just in case
            raise last_exception  # type: ignore
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def timeout_handler(
    *,
    timeout_seconds: float,
    timeout_message: str | None = None,
) -> Callable:
    """Decorator for adding timeout to functions."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            # For sync functions, we can't easily implement timeout without threading
            # This is a placeholder - in practice, you'd use signal or threading
            return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except TimeoutError:
                message = timeout_message or f"Function {func.__name__} timed out after {timeout_seconds} seconds"
                _logger.error(
                    "function_timeout",
                    function=func.__name__,
                    timeout_seconds=timeout_seconds,
                )
                raise TimeoutError(message)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class ErrorContext:
    """Context manager for error handling and logging."""
    
    def __init__(
        self,
        operation: str,
        *,
        component: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.operation = operation
        self.component = component
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.start_time = time.time()
        self.error_count = 0
    
    def __enter__(self) -> ErrorContext:
        _logger.info(
            "operation_started",
            operation=self.operation,
            component=self.component,
            user_id=self.user_id,
            session_id=self.session_id,
            metadata=self.metadata,
        )
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        duration = time.time() - self.start_time
        
        if exc_type is None:
            # Operation completed successfully
            _logger.info(
                "operation_completed",
                operation=self.operation,
                component=self.component,
                duration=duration,
                error_count=self.error_count,
            )
            return False
        
        # Operation failed with an exception
        self.error_count += 1
        
        # Determine if it's our custom exception
        is_mindflow_error = isinstance(exc_val, MindFlowError)
        
        log_data = {
            "operation": self.operation,
            "component": self.component,
            "duration": duration,
            "error_count": self.error_count,
            "error_type": exc_type.__name__,
            "error_message": str(exc_val),
        }
        
        if is_mindflow_error:
            log_data.update({
                "error_id": getattr(exc_val, 'error_id', None),
                "error_code": getattr(exc_val, 'error_code', None),
            })
        
        if self.user_id:
            log_data["user_id"] = self.user_id
        
        if self.session_id:
            log_data["session_id"] = self.session_id
        
        _logger.error("operation_failed", **log_data)
        
        # Don't suppress the exception
        return False
    
    def record_error(self, error: Exception) -> None:
        """Record an error that occurred during the operation."""
        self.error_count += 1
        _logger.warning(
            "operation_error",
            operation=self.operation,
            component=self.component,
            error_type=error.__class__.__name__,
            error_message=str(error),
            total_errors=self.error_count,
        )


class CircuitBreaker:
    """Simple circuit breaker implementation for fault tolerance."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return self._call_with_circuit_breaker(func, *args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await self._call_with_circuit_breaker_async(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    def _call_with_circuit_breaker(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                _logger.info("circuit_breaker_half_open", function=func.__name__)
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise
    
    async def _call_with_circuit_breaker_async(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                _logger.info("circuit_breaker_half_open", function=func.__name__)
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.last_failure_time is None:
            return False
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            _logger.info("circuit_breaker_closed")
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            _logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


def create_error_context(
    operation: str,
    *,
    component: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    **metadata: Any,
) -> ErrorContext:
    """Create an error context for operation tracking."""
    return ErrorContext(
        operation=operation,
        component=component,
        user_id=user_id,
        session_id=session_id,
        metadata=metadata,
    )
