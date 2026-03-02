from __future__ import annotations

from collections import deque
from omnimind_backend.schemas.decomposition import DTSession, DTTask
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class Scheduler:
    """Determine execution order for sub-tasks based on dependencies (Topological Sort)."""

    def get_execution_order(self, session: DTSession) -> list[DTTask]:
        """Return tasks in an order that satisfies all dependencies."""
        tasks_dict = {t.id: t for t in session.tasks}
        
        # Build dependency graph
        adj = {t.id: [] for t in session.tasks}
        in_degree = {t.id: 0 for t in session.tasks}
        
        for t in session.tasks:
            for dep in t.dependencies:
                if dep in adj:
                    adj[dep].append(t.id)
                    in_degree[t.id] += 1
                else:
                    _logger.warning("unknown_dependency", task_id=t.id, dependency=dep)

        # Kahn's algorithm for topological sort
        queue = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
        ordered_task_ids = []
        
        while queue:
            u = queue.popleft()
            ordered_task_ids.append(u)
            
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        # Check for cycles
        if len(ordered_task_ids) != len(session.tasks):
            _logger.error("cycle_detected_in_dependencies", session_id=session.id)
            
        return [tasks_dict[t_id] for t_id in ordered_task_ids]
