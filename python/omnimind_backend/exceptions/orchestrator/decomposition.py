"""Task decomposition exceptions.

Exceptions for task analysis, decomposition failures,
and subtask generation errors.
"""

from __future__ import annotations

from omnimind_backend.exceptions.base.business import WorkflowError


class DecompositionError(WorkflowError):
    """Task decomposition failure."""
    
    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        task_description: str | None = None,
        decomposition_method: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="decomposition",
            component="orchestrator",
            **kwargs
        )
        self.task_id = task_id
        self.task_description = task_description
        self.decomposition_method = decomposition_method
