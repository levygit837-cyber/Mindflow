"""Orchestration services for MindFlow backend.

This module provides services for task decomposition, agent coordination,
and intelligent routing in complex workflows.
"""

from __future__ import annotations


# Factory functions for orchestration services
def get_orchestration_service():
    """Factory function for OrchestrationService."""
    from mindflow_backend.services.orchestration.orchestration_service import OrchestrationService
    return OrchestrationService()

def get_task_service():
    """Factory function for TaskService."""
    from mindflow_backend.services.orchestration.task_service import TaskService
    return TaskService()

def get_routing_service():
    """Factory function for RoutingService."""
    from mindflow_backend.services.orchestration.routing_service import RoutingService
    return RoutingService()


def get_session_runtime_state_service():
    """Factory function for the shared session runtime state service."""
    from mindflow_backend.services.core import (
        get_session_runtime_state_service as get_core_session_runtime_state_service,
    )

    return get_core_session_runtime_state_service()


_todo_planning_service = None
_execution_task_service = None
_planning_service = None
_task_management_service = None


def get_task_management_service():
    """Factory function for the TaskManagementService."""
    global _task_management_service
    if _task_management_service is None:
        from mindflow_backend.services.orchestration.task_management_service import (
            TaskManagementService,
        )
        _task_management_service = TaskManagementService()
    return _task_management_service


def get_todo_planning_service():
    """Factory function for the session-scoped TodoPlanningService.

    Returns either the legacy in-memory implementation or the new task-based
    implementation depending on the USE_TASK_BASED_TODO feature flag.

    Feature flag: USE_TASK_BASED_TODO (default: False)
    - False: Use legacy in-memory TodoPlanningService
    - True: Use new TaskBasedTodoPlanningService with PostgreSQL backend
    """
    global _todo_planning_service
    if _todo_planning_service is None:
        import os
        use_task_based = os.environ.get("USE_TASK_BASED_TODO", "false").lower() == "true"

        if use_task_based:
            from mindflow_backend.services.orchestration.task_based_todo_planning_service import (
                TaskBasedTodoPlanningService,
            )
            from mindflow_backend.infra.logging import get_logger

            _logger = get_logger(__name__)
            _logger.info(
                "todo_planning_service_initialized",
                implementation="task_based",
                backend="postgresql",
            )
            _todo_planning_service = TaskBasedTodoPlanningService()
        else:
            from mindflow_backend.services.orchestration.todo_planning_service import (
                TodoPlanningService,
            )
            from mindflow_backend.infra.logging import get_logger
            import warnings

            _logger = get_logger(__name__)
            _logger.warning(
                "todo_planning_service_initialized",
                implementation="legacy_in_memory",
                deprecation_warning="In-memory TodoPlanningService is deprecated. "
                "Set USE_TASK_BASED_TODO=true to use the new PostgreSQL-backed implementation.",
            )
            warnings.warn(
                "TodoPlanningService in-memory implementation is deprecated. "
                "Set USE_TASK_BASED_TODO=true environment variable to use the new "
                "TaskBasedTodoPlanningService with persistent PostgreSQL storage.",
                DeprecationWarning,
                stacklevel=2,
            )
            _todo_planning_service = TodoPlanningService()
    return _todo_planning_service


def get_execution_task_service():
    """Factory function for the session-scoped runtime ExecutionTaskService."""
    global _execution_task_service
    if _execution_task_service is None:
        from mindflow_backend.services.orchestration.execution_task_service import (
            ExecutionTaskService,
        )

        _execution_task_service = ExecutionTaskService()
    return _execution_task_service


def get_planning_service():
    """Factory function for the PlanningService."""
    global _planning_service
    if _planning_service is None:
        from mindflow_backend.services.orchestration.planning_service import PlanningService
        _planning_service = PlanningService()
    return _planning_service


# Public exports
__all__ = [
    "get_orchestration_service",
    "get_task_service",
    "get_task_management_service",
    "get_routing_service",
    "get_session_runtime_state_service",
    "get_todo_planning_service",
    "get_execution_task_service",
    "get_planning_service",
]
