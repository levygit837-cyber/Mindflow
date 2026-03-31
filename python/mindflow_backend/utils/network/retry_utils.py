"""Retry utilities for network operations.

Provides decorators and functions for retrying network operations.
"""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)
T = TypeVar('T')


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


def retry_with_jitter(
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter_factor: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_attempts: bool = True,
) -> Callable:
    """Decorator for retrying with jitter to avoid thundering herd."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        if log_attempts:
                            _logger.error(
                                "retry_with_jitter_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    # Calculate delay with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * jitter_factor * (0.5 - (hash(str(attempt)) % 100) / 100)
                    actual_delay = delay + jitter
                    
                    if log_attempts:
                        _logger.warning(
                            "retry_with_jitter_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=actual_delay,
                            error=str(exc),
                        )
                    
                    time.sleep(max(0, actual_delay))
            
            raise last_exception  # type: ignore
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        if log_attempts:
                            _logger.error(
                                "async_retry_with_jitter_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    # Calculate delay with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * jitter_factor * (0.5 - (hash(str(attempt)) % 100) / 100)
                    actual_delay = delay + jitter
                    
                    if log_attempts:
                        _logger.warning(
                            "async_retry_with_jitter_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=actual_delay,
                            error=str(exc),
                        )
                    
                    await asyncio.sleep(max(0, actual_delay))
            
            raise last_exception  # type: ignore
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def exponential_backoff_retry(
    *,
    max_attempts: int = 5,
    initial_delay: float = 0.1,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_attempts: bool = True,
) -> Callable:
    """Decorator for retrying with exponential backoff."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = initial_delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        if log_attempts:
                            _logger.error(
                                "exponential_backoff_retry_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    if log_attempts:
                        _logger.warning(
                            "exponential_backoff_retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(exc),
                        )
                    
                    time.sleep(current_delay)
                    current_delay = min(current_delay * multiplier, max_delay)
            
            raise last_exception  # type: ignore
        
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = initial_delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        if log_attempts:
                            _logger.error(
                                "async_exponential_backoff_retry_failed",
                                function=func.__name__,
                                attempt=attempt + 1,
                                max_attempts=max_attempts,
                                error=str(exc),
                            )
                        raise
                    
                    if log_attempts:
                        _logger.warning(
                            "async_exponential_backoff_retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_attempts=max_attempts,
                            delay=current_delay,
                            error=str(exc),
                        )
                    
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * multiplier, max_delay)
            
            raise last_exception  # type: ignore
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class RetryState:
    """State tracker for retry operations."""
    
    def __init__(self, max_attempts: int):
        self.max_attempts = max_attempts
        self.attempt = 0
        self.last_exception = None
        self.start_time = time.time()
        self.total_attempts = 0
    
    def should_retry(self, exception: Exception) -> bool:
        """Check if should retry based on state."""
        self.attempt += 1
        self.total_attempts += 1
        self.last_exception = exception
        return self.attempt < self.max_attempts
    
    def get_delay(self, base_delay: float, backoff_factor: float) -> float:
        """Calculate delay for next retry."""
        return base_delay * (backoff_factor ** (self.attempt - 1))
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of retry operation."""
        return {
            "total_attempts": self.total_attempts,
            "max_attempts": self.max_attempts,
            "duration": time.time() - self.start_time,
            "last_exception": str(self.last_exception) if self.last_exception else None,
            "success": self.last_exception is None,
        }


async def retry_async_with_state(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    log_attempts: bool = True,
    **kwargs: Any,
) -> tuple[T, RetryState]:
    """Retry async function with state tracking."""
    state = RetryState(max_attempts)
    
    while True:
        try:
            result = await func(*args, **kwargs)
            return result, state
        except exceptions as exc:
            if not state.should_retry(exc):
                if log_attempts:
                    _logger.error(
                        "async_retry_with_state_failed",
                        function=func.__name__,
                        summary=state.get_summary(),
                    )
                raise
            
            current_delay = state.get_delay(delay, backoff_factor)
            
            if log_attempts:
                _logger.warning(
                    "async_retry_with_state_attempt",
                    function=func.__name__,
                    attempt=state.attempt,
                    delay=current_delay,
                    error=str(exc),
                )
            
            await asyncio.sleep(current_delay)
