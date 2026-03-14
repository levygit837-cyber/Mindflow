"""Sequential Workflow Graph - Defines sequential execution workflows.

This graph implements workflow patterns where steps execute
in sequence, with support for branching, error handling, and state management.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
import asyncio

from mindflow_backend.graphs.base.graph import BaseGraph, GraphType, GraphState
from mindflow_backend.nodes.base.node import BaseNode
from mindflow_backend.nodes.base.stateful import StatefulNode


class SequentialWorkflowGraph(BaseGraph):
    """Graph that implements sequential workflow patterns.
    
    This graph supports:
    - Linear sequential execution
    - Conditional branching within sequences
    - Error recovery and retry logic
    - State persistence across steps
    - Parallel sub-workflows within sequences
    """
    
    def __init__(
        self,
        graph_id: str = "sequential_workflow",
        steps: List[Dict[str, Any]] = None,
        error_handling: str = "continue",  # continue, stop, retry
        max_retries: int = 3,
        state_persistence: bool = True,
        timeout_per_step: Optional[Dict[str, float]] = None,
        description: str = ""
    ) -> None:
        super().__init__(
            graph_id=graph_id,
            graph_type=GraphType.SEQUENTIAL,
            description=description or "Sequential workflow execution"
        )
        
        self.steps = steps or []
        self.error_handling = error_handling.lower()
        self.max_retries = max_retries
        self.state_persistence = state_persistence
        self.timeout_per_step = timeout_per_step or {}
        
        # Internal state
        self._workflow_state = {}
        self._execution_history = []
        self._current_step_index = 0
        self._retry_count = 0
    
    def add_step(
        self,
        step_id: str,
        node: Union[BaseNode, str],
        step_type: str = "process",  # process, condition, branch, merge
        condition: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        retry_on_error: bool = False,
        description: str = ""
    ) -> None:
        """Add a step to the workflow."""
        step = {
            "step_id": step_id,
            "node": node,
            "step_type": step_type,
            "condition": condition,
            "timeout": timeout,
            "retry_on_error": retry_on_error,
            "description": description
        }
        
        self.steps.append(step)
    
    def add_condition_step(
        self,
        step_id: str,
        condition: Dict[str, Any],
        true_step_id: str,
        false_step_id: Optional[str] = None,
        description: str = ""
    ) -> None:
        """Add a conditional branching step."""
        self.add_step(
            step_id=step_id,
            node="condition",  # Will be resolved to actual node
            step_type="condition",
            condition=condition,
            true_step_id=true_step_id,
            false_step_id=false_step_id,
            description=description
        )
    
    def add_parallel_step(
        self,
        step_id: str,
        nodes: List[Union[BaseNode, str]],
        wait_for_all: bool = True,
        timeout: Optional[float] = None,
        description: str = ""
    ) -> None:
        """Add a parallel execution step."""
        self.add_step(
            step_id=step_id,
            node=nodes,
            step_type="parallel",
            condition={"wait_for_all": wait_for_all},
            timeout=timeout,
            description=description
        )
    
    def add_merge_step(
        self,
        step_id: str,
        input_steps: List[str],
        merge_function: str = "last",  # first, last, all, custom
        description: str = ""
    ) -> None:
        """Add a merge step that combines multiple inputs."""
        self.add_step(
            step_id=step_id,
            node="merge",  # Will be resolved to actual merge logic
            step_type="merge",
            condition={
                "input_steps": input_steps,
                "merge_function": merge_function
            },
            description=description
        )
    
    async def execute(self, initial_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the sequential workflow."""
        workflow_state = initial_state or {}
        workflow_state.update(self._workflow_state)
        
        self._execution_history = []
        self._current_step_index = 0
        self._retry_count = 0
        
        try:
            while self._current_step_index < len(self.steps):
                step = self.steps[self._current_step_index]
                step_result = await self._execute_step(step, workflow_state)
                
                # Update workflow state
                if self.state_persistence:
                    workflow_state.update(step_result.get("state_updates", {}))
                
                # Store step result
                self._execution_history.append({
                    "step_id": step["step_id"],
                    "step_type": step["step_type"],
                    "status": step_result.get("status", "completed"),
                    "result": step_result.get("result"),
                    "error": step_result.get("error"),
                    "execution_time": step_result.get("execution_time", 0),
                    "retry_count": self._retry_count
                })
                
                # Handle step completion
                if step_result.get("status") == "completed":
                    self._current_step_index += 1
                    self._retry_count = 0
                elif step_result.get("status") == "failed":
                    if step.get("retry_on_error", False) or self._retry_count < self.max_retries:
                        self._retry_count += 1
                    else:
                        if self.error_handling == "stop":
                            break
                        elif self.error_handling == "continue":
                            self._current_step_index += 1
                            self._retry_count = 0
                elif step_result.get("status") == "branch":
                    # Handle conditional branching
                    branch_result = step_result.get("branch_result")
                    if branch_result:
                        self._current_step_index = self._find_step_index(branch_result)
                        self._retry_count = 0
                    else:
                        # No branch taken, continue to next step
                        self._current_step_index += 1
                        self._retry_count = 0
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "completed" if self._current_step_index >= len(self.steps) else "in_progress",
                "steps_completed": self._current_step_index,
                "total_steps": len(self.steps)
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("sequential_workflow_execution_failed", error=str(e))
            
            return {
                "workflow_state": workflow_state,
                "execution_history": self._execution_history,
                "final_state": "failed",
                "error": str(e),
                "steps_completed": self._current_step_index,
                "total_steps": len(self.steps)
            }
    
    async def _execute_step(self, step: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step."""
        step_id = step["step_id"]
        step_type = step["step_type"]
        start_time = asyncio.get_event_loop().time()
        
        try:
            if step_type == "process":
                return await self._execute_process_step(step, workflow_state)
            elif step_type == "condition":
                return await self._execute_condition_step(step, workflow_state)
            elif step_type == "parallel":
                return await self._execute_parallel_step(step, workflow_state)
            elif step_type == "merge":
                return await self._execute_merge_step(step, workflow_state)
            else:
                raise ValueError(f"Unsupported step type: {step_type}")
                
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "state_updates": {}
            }
    
    async def _execute_process_step(self, step: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a processing step."""
        node = step["node"]
        timeout = step.get("timeout", self.timeout_per_step.get(step["step_id"]))
        
        # Resolve node reference
        if isinstance(node, str):
            from mindflow_backend.graphs.factory import get_graph_factory
            factory = get_graph_factory()
            node_instance = factory.get_node(node)
            if not node_instance:
                raise ValueError(f"Node not found: {node}")
        else:
            node_instance = node
        
        # Prepare step state
        step_state = {
            "step_id": step["step_id"],
            "workflow_state": workflow_state,
            "step_config": step
        }
        
        # Execute node with timeout
        try:
            if timeout:
                result = await asyncio.wait_for(
                    node_instance.execute(step_state),
                    timeout=timeout
                )
            else:
                result = await node_instance.execute(step_state)
            
            execution_time = asyncio.get_event_loop().time() - asyncio.get_event_loop().time()
            
            return {
                "status": "completed",
                "result": result,
                "execution_time": execution_time,
                "state_updates": {"step_result": result}
            }
            
        except asyncio.TimeoutError:
            execution_time = asyncio.get_event_loop().time() - asyncio.get_event_loop().time()
            
            return {
                "status": "timeout",
                "error": f"Step {step['step_id']} timed out after {timeout}s",
                "execution_time": execution_time,
                "state_updates": {}
            }
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - asyncio.get_event_loop().time()
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "state_updates": {}
            }
    
    async def _execute_condition_step(self, step: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a conditional branching step."""
        condition = step.get("condition", {})
        true_step_id = step.get("true_step_id")
        false_step_id = step.get("false_step_id")
        
        # Evaluate condition
        condition_met = self._evaluate_condition(condition, workflow_state)
        
        if condition_met and true_step_id:
            next_step_index = self._find_step_index(true_step_id)
        elif false_step_id:
            next_step_index = self._find_step_index(false_step_id)
        else:
            # No branch taken, continue to next step
            next_step_index = self._current_step_index + 1
        
        return {
            "status": "completed",
            "branch_result": true_step_id if condition_met else false_step_id,
            "next_step_index": next_step_index,
            "execution_time": 0,
            "state_updates": {"condition_met": condition_met}
        }
    
    async def _execute_parallel_step(self, step: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a parallel step."""
        nodes = step["node"]
        condition = step.get("condition", {})
        wait_for_all = condition.get("wait_for_all", True)
        timeout = step.get("timeout", self.timeout_per_step.get(step["step_id"]))
        
        # Resolve node references
        node_instances = []
        for node_ref in nodes:
            if isinstance(node_ref, str):
                from mindflow_backend.graphs.factory import get_graph_factory
                factory = get_graph_factory()
                node_instance = factory.get_node(node_ref)
                if not node_instance:
                    raise ValueError(f"Node not found: {node_ref}")
            else:
                node_instance = node_ref
            
            node_instances.append(node_instance)
        
        # Prepare step state for each node
        step_state = {
            "step_id": step["step_id"],
            "workflow_state": workflow_state,
            "step_config": step
        }
        
        try:
            # Execute all nodes in parallel
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*[
                        node_instance.execute({
                            **step_state,
                            "node_index": i
                        }) for i, node_instance in enumerate(node_instances)
                    ]),
                    timeout=timeout
                )
            else:
                results = await asyncio.gather(*[
                    node_instance.execute({
                        **step_state,
                        "node_index": i
                    }) for i, node_instance in enumerate(node_instances)
                ])
            
            # Process results based on wait_for_all setting
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "node_index": i,
                        "error": str(result)
                    })
                elif wait_for_all:
                    successful_results.append({
                        "node_index": i,
                        "result": result
                    })
                else:
                    # At least one success is enough
                    successful_results.append({
                        "node_index": i,
                        "result": result
                    })
            
            execution_time = 0  # Would be measured properly
            
            status = "completed" if successful_results else "failed"
            
            return {
                "status": status,
                "parallel_results": {
                    "successful": successful_results,
                    "failed": failed_results
                },
                "execution_time": execution_time,
                "state_updates": {
                    "parallel_success_count": len(successful_results),
                    "parallel_failed_count": len(failed_results)
                }
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "error": f"Parallel step {step['step_id']} timed out after {timeout}s",
                "execution_time": timeout,
                "state_updates": {}
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": 0,
                "state_updates": {}
            }
    
    async def _execute_merge_step(self, step: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a merge step."""
        input_steps = step.get("condition", {}).get("input_steps", [])
        merge_function = step.get("condition", {}).get("merge_function", "last")
        
        # Collect results from input steps
        input_results = []
        for input_step_id in input_steps:
            # Find the execution history for this step
            step_history = [
                hist for hist in self._execution_history
                if hist.get("step_id") == input_step_id and hist.get("status") == "completed"
            ]
            
            if step_history:
                # Get the most recent successful result
                last_result = step_history[-1].get("result")
                if last_result:
                    input_results.append(last_result)
        
        # Apply merge function
        if merge_function == "first":
            merged_result = input_results[0] if input_results else None
        elif merge_function == "last":
            merged_result = input_results[-1] if input_results else None
        elif merge_function == "all":
            # Combine all results
            merged_result = self._combine_all_results(input_results)
        else:
            # Custom merge function would be called here
            merged_result = None
        
        return {
            "status": "completed",
            "merged_result": merged_result,
            "input_count": len(input_results),
            "execution_time": 0,
            "state_updates": {"merged_result": merged_result}
        }
    
    def _combine_all_results(self, results: List[Any]) -> Any:
        """Combine all results from input steps."""
        if not results:
            return None
        
        # Try to merge lists
        if all(isinstance(result, list) for result in results):
            combined = []
            for result_list in results:
                combined.extend(result_list)
            return combined
        
        # Try to merge dictionaries
        if all(isinstance(result, dict) for result in results):
            combined = {}
            for result_dict in results:
                combined.update(result_dict)
            return combined
        
        # Mixed types - return as list
        return results
    
    def _evaluate_condition(self, condition: Dict[str, Any], workflow_state: Dict[str, Any]) -> bool:
        """Evaluate a condition for conditional branching."""
        for field, expected_value in condition.items():
            if field.startswith("state."):
                # Check workflow state
                state_field = field[6:]  # Remove "state." prefix
                actual_value = workflow_state.get(state_field)
            else:
                # Check step result or other data
                actual_value = workflow_state.get(field)
            
            if actual_value != expected_value:
                return False
        
        return True
    
    def _find_step_index(self, step_id: str) -> int:
        """Find the index of a step by ID."""
        for i, step in enumerate(self.steps):
            if step["step_id"] == step_id:
                return i
        return -1
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """Get information about the workflow configuration."""
        return {
            "graph_id": self.graph_id,
            "total_steps": len(self.steps),
            "current_step_index": self._current_step_index,
            "error_handling": self.error_handling,
            "max_retries": self.max_retries,
            "state_persistence": self.state_persistence,
            "has_timeouts": bool(self.timeout_per_step),
            "execution_history_count": len(self._execution_history)
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the execution history."""
        return self._execution_history[-limit:] if len(self._execution_history) > limit else self._execution_history
    
    def reset_workflow_state(self) -> None:
        """Reset the workflow state."""
        self._workflow_state = {}
        self._current_step_index = 0
        self._retry_count = 0
        self._execution_history = []
