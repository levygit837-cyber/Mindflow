"""SemanticScheduler — topological sort of SubTaskContracts.

Uses Kahn's algorithm keyed by ``task_id`` UUIDs.
Raises ``ValueError`` on dependency cycles.
"""

from __future__ import annotations

from collections import deque
from uuid import UUID

from omnimind_backend.decomposition.engine import TaskScheduler
from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubTaskContract


class SemanticScheduler(TaskScheduler):
    """Order sub-tasks respecting their dependency graph (Kahn's algorithm)."""

    def get_execution_order(
        self,
        components: list[SubTaskContract],
    ) -> list[SubTaskContract]:
        """Return *components* in a dependency-safe execution order.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        by_id: dict[UUID, SubTaskContract] = {c.task_id: c for c in components}

        # Build adjacency list and in-degree map
        adj: dict[UUID, list[UUID]] = {c.task_id: [] for c in components}
        in_degree: dict[UUID, int] = {c.task_id: 0 for c in components}

        for c in components:
            for dep in c.dependencies:
                if dep not in adj:
                    continue  # unknown dependency — skip silently
                adj[dep].append(c.task_id)
                in_degree[c.task_id] += 1

        # Kahn's BFS
        queue: deque[UUID] = deque(
            tid for tid, deg in in_degree.items() if deg == 0
        )
        ordered: list[UUID] = []

        while queue:
            u = queue.popleft()
            ordered.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        if len(ordered) != len(components):
            raise ValueError(
                f"Dependency cycle detected: "
                f"resolved {len(ordered)}/{len(components)} tasks"
            )

        return [by_id[tid] for tid in ordered]
