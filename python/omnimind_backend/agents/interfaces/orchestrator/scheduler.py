"""Scheduler interface.

Defines the contract for ordering sub-tasks by dependency
resolution (topological sort).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubTaskContract


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Contract for task scheduling implementations."""

    def get_execution_order(
        self,
        components: list[SubTaskContract],
    ) -> list[SubTaskContract]:
        """Return tasks in dependency-respecting execution order.

        Args:
            components: Unordered list of sub-task contracts.

        Returns:
            Topologically sorted list of tasks.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        ...
