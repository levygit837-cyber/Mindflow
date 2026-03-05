"""Timeout exceptions.

Exceptions for operation timeouts, deadline exceeded,
and time limit errors.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.core import TimeoutError as BaseTimeoutError


class TimeoutError(BaseTimeoutError):
    """Runtime operation timeout."""
    
    def __init__(
        self,
        message: str,
        *,
        operation_type: str | None = None,
        timeout_seconds: float | None = None,
        actual_duration_ms: int | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            operation=operation_type,
            timeout_seconds=timeout_seconds,
            component="runtime",
            **kwargs
        )
        self.operation_type = operation_type
        self.actual_duration_ms = actual_duration_ms
