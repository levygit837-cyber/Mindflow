"""Graph execution exceptions.

Exceptions for LangGraph execution, node failures,
and graph traversal errors.
"""

from __future__ import annotations

from mindflow_backend.exceptions.base.business import WorkflowError


class GraphExecutionError(WorkflowError):
    """Graph execution failure."""
    
    def __init__(
        self,
        message: str,
        *,
        graph_id: str | None = None,
        node_name: str | None = None,
        execution_phase: str | None = None,
        **kwargs,
    ):
        super().__init__(
            message,
            workflow_step="graph_execution",
            component="orchestrator",
            **kwargs
        )
        self.graph_id = graph_id
        self.node_name = node_name
        self.execution_phase = execution_phase
