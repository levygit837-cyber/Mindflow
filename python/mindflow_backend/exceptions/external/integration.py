"""Integration exceptions.

Exceptions for system integration failures, data synchronization,
and cross-service communication errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business_new import WorkflowError


class IntegrationError(WorkflowError):
    """System integration failure."""
    
    def __init__(
        self,
        message: str,
        *,
        source_system: str | None = None,
        target_system: str | None = None,
        integration_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="integration",
            component="external",
            **kwargs
        )
        self.source_system = source_system
        self.target_system = target_system
        self.integration_type = integration_type
