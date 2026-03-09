"""Resilience pattern exceptions.

Exceptions for circuit breakers, retry mechanisms,
and fault tolerance patterns.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.core_new import InfrastructureError


class CircuitOpenError(InfrastructureError):
    """Circuit breaker is open."""
    
    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        failure_count: int | None = None,
        reset_timeout: int | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            service="circuit_breaker",
            component="infrastructure",
            **kwargs
        )
        self.service_name = service_name
        self.failure_count = failure_count
        self.reset_timeout = reset_timeout
