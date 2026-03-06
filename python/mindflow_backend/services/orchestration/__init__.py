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

# Public exports
__all__ = [
    "get_orchestration_service",
    "get_task_service",
    "get_routing_service",
]
