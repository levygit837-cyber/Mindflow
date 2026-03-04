"""Scheduler interface.

Defines the contract for ordering sub-components by dependency
resolution (topological sort).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubComponentContract


@runtime_checkable
class SchedulerProtocol(Protocol):
    """Contract for component scheduling implementations."""

    def get_execution_order(
        self,
        components: list[SubComponentContract],
    ) -> list[SubComponentContract]:
        """Return components in dependency-respecting execution order.

        Args:
            components: Unordered list of sub-component contracts.

        Returns:
            Topologically sorted list of components.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        ...
