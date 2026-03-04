"""DT v2 Scheduler — topological sort by UUID-keyed dependencies.

Implements SchedulerProtocol using Kahn's algorithm.
Unlike v1 (which accepts DTSession), this works directly with
a list of SubComponentContract and raises ValueError on cycles.
"""

from __future__ import annotations

from collections import deque
from uuid import UUID

from omnimind_backend.schemas.orchestration.decomposition.decomposition_v2 import SubComponentContract


class SchedulerV2:
    """SchedulerProtocol implementation for v2 contracts."""

    def get_execution_order(
        self,
        components: list[SubComponentContract],
    ) -> list[SubComponentContract]:
        """Return components in dependency-respecting execution order.

        Uses Kahn's algorithm for topological sort keyed by UUID.

        Raises:
            ValueError: If a dependency cycle is detected.
        """
        by_id: dict[UUID, SubComponentContract] = {
            c.component_id: c for c in components
        }

        # Build adjacency list and in-degree map
        adj: dict[UUID, list[UUID]] = {c.component_id: [] for c in components}
        in_degree: dict[UUID, int] = {c.component_id: 0 for c in components}

        for c in components:
            for dep in c.dependencies:
                if dep not in adj:
                    # Skip unknown dependencies silently
                    continue
                adj[dep].append(c.component_id)
                in_degree[c.component_id] += 1

        # Kahn's algorithm
        queue: deque[UUID] = deque(
            cid for cid, deg in in_degree.items() if deg == 0
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
            msg = (
                f"Dependency cycle detected: "
                f"resolved {len(ordered)}/{len(components)} components"
            )
            raise ValueError(msg)

        return [by_id[cid] for cid in ordered]
