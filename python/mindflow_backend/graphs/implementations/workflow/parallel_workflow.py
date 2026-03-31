"""Parallel Workflow Graph - Defines parallel execution workflows.

This graph implements workflow patterns where multiple branches execute
concurrently with support for synchronization and result aggregation.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mindflow_backend.graphs.base.graph import BaseGraph, GraphType
from mindflow_backend.nodes.base.node import BaseNode


class ParallelWorkflowGraph(BaseGraph):
    """Graph that implements parallel workflow patterns.
    
    This graph supports:
    - Parallel branch execution
    - Race conditions (first to complete)
    - Fork/Join patterns
    - Concurrent data processing
    - Synchronization points
    """
    
    def __init__(
        self,
        graph_id: str = "parallel_workflow",
        branches: list[dict[str, Any]] = None,
        join_type: str = "all",  # all, any, first, custom
        synchronization_points: list[dict[str, Any]] = None,
        timeout: float | None = None,
        description: str = ""
    ) -> None:
        super().__init__(
            graph_id=graph_id,
            graph_type=GraphType.PARALLEL,
            description=description or "Parallel workflow execution"
        )
        
        self.branches = branches or []
        self.join_type = join_type.lower()
        self.synchronization_points = synchronization_points or []
        self.timeout = timeout
        
        # Internal state
        self._workflow_state = {}
        self._execution_history = []
        self._branch_results = {}
        self._current_phase = "initialization"
    
    def add_branch(
        self,
        branch_id: str,
        nodes: list[BaseNode | str],
        condition: dict[str, Any] | None = None,
        weight: float = 1.0,
        description: str = ""
    ) -> None:
        """Add a parallel branch to the workflow."""
        branch = {
            "branch_id": branch_id,
            "nodes": nodes,
            "condition": condition,
            "weight": weight,
            "description": description
        }
        
        self.branches.append(branch)
    
    def add_synchronization_point(
        self,
        point_id: str,
        participants: list[str],  # Branch IDs that must sync
        sync_type: str = "barrier",  # barrier, semaphore, mutex
        description: str = ""
    ) -> None:
        """Add a synchronization point to the workflow."""
        sync_point = {
            "point_id": point_id,
            "sync_type": sync_type,
            "participants": participants,
            "description": description
        }
        
        self.synchronization_points.append(sync_point)
    
    def add_fork_join(
        self,
        fork_id: str,
        fork_branches: list[str],
        join_point: str,
        join_type: str = "wait_all",  # wait_all, wait_any, merge, custom
        description: str = ""
    ) -> None:
        """Add a fork-join pattern to the workflow."""
        # This would be stored and processed during execution
        pass
    
    async def execute(self, initial_state: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the parallel workflow."""
        workflow_state = initial_state or {}
        workflow_state.update(self._workflow_state)
        
        self._execution_history = []
        self._branch_results = {}
        self._current_phase = "branch_execution"
        
        try:
            # Phase 1: Evaluate branch conditions
            active_branches = await self._evaluate_branch_conditions(workflow_state)
            
            # Phase 2: Execute active branches in parallel
            if active_branches:
                branch_results = await self._execute_parallel_branches(active_branches, workflow_state)
                self._branch_results.update(branch_results)
            
            # Phase 3: Apply join condition
            final_result = await self._apply_join_condition(branch_results, workflow_state)
            
            # Phase 4: Synchronization points (if any)
            if self.synchronization_points:
                await self._execute_synchronization_points(workflow_state)
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "completed",
                "branch_results": self._branch_results,
                "final_result": final_result,
                "active_branches": len(active_branches),
                "total_branches": len(self.branches)
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("parallel_workflow_execution_failed", error=str(e))
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "failed",
                "error": str(e),
                "branch_results": {},
                "final_result": None,
                "active_branches": 0,
                "total_branches": len(self.branches)
            }
    
    async def _evaluate_branch_conditions(self, workflow_state: dict[str, Any]) -> list[dict[str, Any]]:
        """Evaluate conditions for all branches and return active ones."""
        active_branches = []
        
        for branch in self.branches:
            condition = branch.get("condition")
            
            if not condition:
                # No condition means branch is always active
                active_branches.append(branch)
            else:
                # Evaluate condition
                condition_met = self._evaluate_condition(condition, workflow_state)
                
                if condition_met:
                    active_branches.append(branch)
        
        return active_branches
    
    async def _execute_parallel_branches(self, branches: list[dict[str, Any]], workflow_state: dict[str, Any]) -> dict[str, Any]:
        """Execute multiple branches in parallel."""
        branch_tasks = []
        
        for branch in branches:
            branch_id = branch["branch_id"]
            nodes = branch["nodes"]
            weight = branch.get("weight", 1.0)
            
            # Create branch execution task
            async def execute_branch():
                branch_state = {
                    "branch_id": branch_id,
                    "workflow_state": workflow_state,
                    "branch_config": branch
                }
                
                # Execute nodes in sequence for this branch
                branch_result = []
                for node in nodes:
                    if isinstance(node, str):
                        from mindflow_backend.graphs.factory import get_graph_factory
                        factory = get_graph_factory()
                        node_instance = factory.get_node(node)
                        if not node_instance:
                            raise ValueError(f"Node not found: {node}")
                    else:
                        node_instance = node
                    
                    node_result = await node_instance.execute(branch_state)
                    branch_result.append(node_result)
                else:
                    node_instance = node
                    node_result = await node_instance.execute(branch_state)
                    branch_result.append(node_result)
                
                return {
                    "branch_id": branch_id,
                    "weight": weight,
                    "result": branch_result,
                    "execution_time": 0  # Would be measured properly
                }
            
            return execute_branch()
        
        # Execute all branches in parallel
        try:
            if self.timeout:
                branch_results = await asyncio.wait_for(
                    asyncio.gather(*[execute_branch() for branch in branches]),
                    timeout=self.timeout
                )
            else:
                branch_results = await asyncio.gather(*[execute_branch() for branch in branches])
            
            # Convert to dictionary format
            result_dict = {}
            for i, result in enumerate(branch_results):
                if isinstance(result, Exception):
                    result_dict[f"branch_{i}_error"] = str(result)
                else:
                    result_dict[f"branch_{i}"] = result
            
            return result_dict
            
        except TimeoutError:
            # Handle timeout
            error_dict = {}
            for i, branch in enumerate(branches):
                error_dict[f"branch_{i}_error"] = f"Branch {branch['branch_id']} timed out"
            
            return error_dict
    
    async def _apply_join_condition(self, branch_results: dict[str, Any], workflow_state: dict[str, Any]) -> Any:
        """Apply the join condition to determine final result."""
        if not branch_results:
            return None
        
        if self.join_type == "all":
            # All branches must complete successfully
            for branch_id, result in branch_results.items():
                if isinstance(result, Exception):
                    return {
                        "join_type": self.join_type,
                        "join_status": "failed",
                        "failed_branch": branch_id,
                        "error": str(result)
                    }
            
            # Return combined results (simplified)
            combined_results = {}
            for branch_id, result in branch_results.items():
                if not isinstance(result, Exception):
                    combined_results[branch_id] = result
            
            # Apply custom join function if needed
            return self._apply_custom_join(combined_results, workflow_state)
        
        elif self.join_type == "any":
            # Return first successful result
            for branch_id, result in branch_results.items():
                if not isinstance(result, Exception):
                    return {
                        "join_type": self.join_type,
                        "join_status": "completed",
                        "selected_branch": branch_id,
                        "result": result
                    }
            
            return None
        
        elif self.join_type == "first":
            # Return result from first branch (by weight or order)
            return self._apply_first_join(branch_results, workflow_state)
        
        else:
            # Custom join type
            return self._apply_custom_join(branch_results, workflow_state)
    
    def _apply_custom_join(self, branch_results: dict[str, Any], workflow_state: dict[str, Any]) -> Any:
        """Apply custom join logic."""
        # This would be implemented based on specific requirements
        # For now, return all results combined
        combined = {}
        for branch_id, result in branch_results.items():
            if not isinstance(result, Exception):
                combined[branch_id] = result
        
        return {
            "join_type": "custom",
            "join_status": "completed",
            "combined_results": combined
        }
    
    def _apply_first_join(self, branch_results: dict[str, Any], workflow_state: dict[str, Any]) -> Any:
        """Apply first-to-complete join logic."""
        # Sort by weight if available, then by order
        branch_list = list(self.branches)
        sorted_branches = sorted(
            branch_results.items(),
            key=lambda x: (-(x[1].get("weight", 1.0)), branch_list.index(x[0]) if x[0] in branch_list else 0)
        )
        
        # Return first successful result
        for branch_id, result in sorted_branches:
            if not isinstance(result, Exception):
                return {
                    "join_type": self.join_type,
                    "join_status": "completed",
                    "selected_branch": branch_id,
                    "result": result
                }
        
        return None
    
    def _evaluate_condition(self, condition: dict[str, Any], workflow_state: dict[str, Any]) -> bool:
        """Evaluate a condition for branch activation."""
        for field, expected_value in condition.items():
            if field.startswith("state."):
                # Check workflow state
                state_field = field[6:]  # Remove "state." prefix
                actual_value = workflow_state.get(state_field)
            else:
                # Check other conditions
                actual_value = workflow_state.get(field)
            
            if actual_value != expected_value:
                return False
        
        return True
    
    async def _execute_synchronization_points(self, workflow_state: dict[str, Any]) -> None:
        """Execute synchronization points."""
        for sync_point in self.synchronization_points:
            sync_type = sync_point.get("sync_type")
            participants = sync_point.get("participants", [])
            
            if sync_type == "barrier":
                await self._execute_barrier(participants, workflow_state)
            elif sync_type == "semaphore":
                await self._execute_semaphore(participants, workflow_state)
            elif sync_type == "mutex":
                await self._execute_mutex(participants, workflow_state)
    
    async def _execute_barrier(self, participants: list[str], workflow_state: dict[str, Any]) -> None:
        """Execute a barrier synchronization point."""
        # This would implement a barrier where all participants wait
        # For now, just log the synchronization
        from mindflow_backend.infra.logging import get_logger
        logger = get_logger(__name__)
        logger.info("barrier_synchronization", participants=participants)
    
    async def _execute_semaphore(self, participants: list[str], workflow_state: dict[str, Any]) -> None:
        """Execute a semaphore synchronization point."""
        # This would implement semaphore logic
        from mindflow_backend.infra.logging import get_logger
        logger = get_logger(__name__)
        logger.info("semaphore_synchronization", participants=participants)
    
    async def _execute_mutex(self, participants: list[str], workflow_state: dict[str, Any]) -> None:
        """Execute a mutex synchronization point."""
        # This would implement mutex logic
        from mindflow_backend.infra.logging import get_logger
        logger = get_logger(__name__)
        logger.info("mutex_synchronization", participants=participants)
    
    def get_workflow_info(self) -> dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            "graph_id": self.graph_id,
            "total_branches": len(self.branches),
            "join_type": self.join_type,
            "has_synchronization": len(self.synchronization_points) > 0,
            "synchronization_points": len(self.synchronization_points),
            "current_phase": self._current_phase,
            "execution_history_count": len(self._execution_history)
        }
