"""Task scheduling exceptions.

Exceptions for task scheduling, dependency resolution,
and execution order failures.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business_new import WorkflowError


class SchedulingError(WorkflowError):
    """Task scheduling failure."""
    
    def __init__(
        self,
        message: str,
        *,
        total_tasks: int | None = None,
        scheduled_tasks: int | None = None,
        algorithm: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="scheduling",
            component="orchestrator",
            **kwargs
        )
        self.total_tasks = total_tasks
        self.scheduled_tasks = scheduled_tasks
        self.algorithm = algorithm
