"""Code execution exceptions.

Exceptions for code execution, sandbox failures,
and tool operation errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business_new import WorkflowError


class ExecutionError(WorkflowError):
    """Code execution failure."""
    
    def __init__(
        self,
        message: str,
        *,
        execution_type: str | None = None,
        sandbox_id: str | None = None,
        tool_name: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="execution",
            component="runtime",
            **kwargs
        )
        self.execution_type = execution_type
        self.sandbox_id = sandbox_id
        self.tool_name = tool_name
