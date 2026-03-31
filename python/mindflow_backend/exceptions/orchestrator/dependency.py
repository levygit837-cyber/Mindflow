"""Dependency resolution exceptions.

Exceptions for dependency management, circular dependencies,
and task dependency failures.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business_new import WorkflowError


class DependencyError(WorkflowError):
    """Dependency resolution failure."""
    
    def __init__(
        self,
        message: str,
        *,
        dependent_task: str | None = None,
        required_task: str | None = None,
        dependency_type: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="dependency_resolution",
            component="orchestrator",
            **kwargs
        )
        self.dependent_task = dependent_task
        self.required_task = required_task
        self.dependency_type = dependency_type
