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
_planning_service = None


def get_todo_planning_service():
    """Factory function for the session-scoped in-memory TodoPlanningService."""
    global _todo_planning_service
    if _todo_planning_service is None:
        from mindflow_backend.services.orchestration.todo_planning_service import (
            TodoPlanningService,
        )
        _todo_planning_service = TodoPlanningService()
    return _todo_planning_service


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
    "get_routing_service",
    "get_session_runtime_state_service",
    "get_todo_planning_service",
    "get_planning_service",
]
