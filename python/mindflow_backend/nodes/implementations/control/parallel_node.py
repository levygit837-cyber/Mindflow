"""Parallel Node - Controls parallel execution in graphs.

This node executes multiple tasks concurrently and aggregates results,
supporting various parallel execution patterns and synchronization strategies.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class ParallelNode(StatefulNode, BaseNode):
    """Node that executes tasks in parallel.
    
    This node supports multiple parallel execution patterns:
    - Parallel all: Execute all tasks concurrently
    - Parallel any: Execute until first success
    - Parallel race: Execute all, return first result
    - Parallel map: Apply function to collection in parallel
    """
    
    def __init__(
        self,
        node_id: str = "parallel",
        execution_mode: str = "all",  # all, any, race, map
        tasks: list[dict[str, Any]] | None = None,
        task_function: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        map_function: Callable[[Any], dict[str, Any]] | None = None,
        collection: list[Any] | None = None,
        timeout: float | None = None,
        max_concurrency: int | None = None,
        error_handling: str = "continue",  # continue, fail, collect
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CONTROL,
            category=NodeCategory.CONTROL_FLOW,
            description=description or f"{execution_mode} parallel execution"
        )
        
        self.execution_mode = execution_mode.lower()
        self.tasks = tasks or []
        self.task_function = task_function
        self.map_function = map_function
        self.collection = collection or []
        self.timeout = timeout
        self.max_concurrency = max_concurrency
        self.error_handling = error_handling.lower()
        
        # Required inputs
        self._setup_required_inputs()
        self.config.outputs = {"result", "parallel_results", "metadata"}
        
        # Internal state
        self._execution_count = 0
        self._parallel_results = {}
    
    def _setup_required_inputs(self) -> None:
        """Setup required inputs based on execution mode."""
        if self.execution_mode in ["all", "any", "race"]:
            self.config.required_inputs = {"tasks"}
        elif self.execution_mode == "map":
            self.config.required_inputs = {"collection", "map_function"}
        else:
            self.config.required_inputs = {"data"}
    
    async def initialize(self) -> None:
        """Initialize the parallel node."""
        await super().initialize()
        
        # Initialize parallel execution state
        self._execution_count = 0
        self._parallel_results = {}
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute parallel tasks based on configured mode."""
        try:
            if self.execution_mode == "all":
                result = await self._execute_parallel_all(state)
            elif self.execution_mode == "any":
                result = await self._execute_parallel_any(state)
            elif self.execution_mode == "race":
                result = await self._execute_parallel_race(state)
            elif self.execution_mode == "map":
                result = await self._execute_parallel_map(state)
            else:
                raise ValueError(f"Unsupported execution mode: {self.execution_mode}")
            
            self._execution_count += 1
            return result
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("parallel_node_execution_failed", 
                       execution_mode=self.execution_mode, 
                       error=str(e))
            
            return {
                "result": None,
                "parallel_results": {},
                "error": str(e),
                "metadata": {"execution_mode": self.execution_mode, "status": "error"}
            }
    
    async def _execute_parallel_all(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute all tasks in parallel and wait for all to complete."""
        tasks = state.get("tasks", self.tasks)
        
        if not tasks:
            return {
                "result": [],
                "parallel_results": {},
                "metadata": {"execution_mode": "all", "status": "no_tasks"}
            }
        
        # Create coroutine list
        coroutines = []
        for i, task in enumerate(tasks):
            if self.task_function:
                coroutines.append(self._execute_task_with_function(task, i))
            else:
                coroutines.append(self._execute_task_direct(task, i))
        
        # Execute with concurrency limit
        semaphore = None
        if self.max_concurrency and self.max_concurrency > 0:
            semaphore = asyncio.Semaphore(self.max_concurrency)
        
        # Execute tasks
        if semaphore:
            async def limited_execute(coro):
                async with semaphore:
                    return await coro()
            results = await asyncio.gather(
                *[limited_execute(coro) for coro in coroutines],
                return_exceptions=True
            )
        else:
            results = await asyncio.gather(
                *coroutines,
                return_exceptions=True
            )
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "task_index": i,
                    "task": tasks[i],
                    "error": str(result)
                })
                
                if self.error_handling == "fail":
                    raise result
            else:
                successful_results.append({
                    "task_index": i,
                    "task": tasks[i],
                    "result": result
                })
        
        self._parallel_results = {
            "successful": successful_results,
            "failed": failed_results,
            "total_tasks": len(tasks)
        }
        
        return {
            "result": successful_results,
            "parallel_results": self._parallel_results,
            "metadata": {
                "execution_mode": "all",
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "total_count": len(tasks)
            }
        }
    
    async def _execute_parallel_any(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute tasks in parallel and return first successful result."""
        tasks = state.get("tasks", self.tasks)
        
        if not tasks:
            return {
                "result": None,
                "parallel_results": {},
                "metadata": {"execution_mode": "any", "status": "no_tasks"}
            }
        
        # Create coroutine list
        coroutines = []
        for i, task in enumerate(tasks):
            coroutines.append(self._execute_task_direct(task, i))
        
        # Execute tasks with timeout handling
        try:
            if self.timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*coroutines, return_exceptions=True),
                    timeout=self.timeout
                )
            else:
                results = await asyncio.gather(*coroutines, return_exceptions=True)
        except TimeoutError:
            # Handle timeout
            return {
                "result": None,
                "parallel_results": {"timeout": True},
                "metadata": {"execution_mode": "any", "status": "timeout"}
            }
        
        # Find first successful result
        first_successful = None
        successful_index = None
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                first_successful = {
                    "task_index": i,
                    "task": tasks[i],
                    "result": result
                }
                successful_index = i
                break
        
        # Collect all results for metadata
        all_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "task_index": i,
                    "task": tasks[i],
                    "error": str(result)
                })
            else:
                all_results.append({
                    "task_index": i,
                    "task": tasks[i],
                    "result": result
                })
        
        self._parallel_results = {
            "first_successful": first_successful,
            "all_results": all_results,
            "failed": failed_results,
            "total_tasks": len(tasks)
        }
        
        return {
            "result": first_successful,
            "parallel_results": self._parallel_results,
            "metadata": {
                "execution_mode": "any",
                "successful_index": successful_index,
                "successful_count": len(all_results) - len(failed_results),
                "failed_count": len(failed_results)
            }
        }
    
    async def _execute_parallel_race(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute tasks in parallel and return first result (race condition)."""
        # Similar to _execute_parallel_any but returns first result regardless of success/failure
        tasks = state.get("tasks", self.tasks)
        
        if not tasks:
            return {
                "result": None,
                "parallel_results": {},
                "metadata": {"execution_mode": "race", "status": "no_tasks"}
            }
        
        # Create coroutine list
        coroutines = []
        for i, task in enumerate(tasks):
            coroutines.append(self._execute_task_direct(task, i))
        
        # Execute tasks
        try:
            if self.timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*coroutines, return_exceptions=True),
                    timeout=self.timeout
                )
            else:
                results = await asyncio.gather(*coroutines, return_exceptions=True)
        except TimeoutError:
            return {
                "result": None,
                "parallel_results": {"timeout": True},
                "metadata": {"execution_mode": "race", "status": "timeout"}
            }
        
        # Return first result (success or failure)
        first_result = None
        first_index = None
        
        if results:
            first_result = results[0]
            first_index = 0
        
        # Collect all results
        all_results = []
        for i, result in enumerate(results):
            all_results.append({
                "task_index": i,
                "task": tasks[i],
                "result": result if not isinstance(result, Exception) else result.__class__.__name__
            })
        
        self._parallel_results = {
            "first_result": first_result,
            "all_results": all_results,
            "total_tasks": len(tasks)
        }
        
        return {
            "result": first_result,
            "parallel_results": self._parallel_results,
            "metadata": {
                "execution_mode": "race",
                "first_index": first_index,
                "total_count": len(tasks)
            }
        }
    
    async def _execute_parallel_map(self, state: dict[str, Any]) -> dict[str, Any]:
        """Apply map function to collection in parallel."""
        collection = state.get("collection", self.collection)
        map_function = state.get("map_function", self.map_function)
        
        if not collection or not map_function:
            return {
                "result": [],
                "parallel_results": {},
                "metadata": {"execution_mode": "map", "status": "missing_inputs"}
            }
        
        # Create coroutines for map operation
        coroutines = []
        for i, item in enumerate(collection):
            coroutines.append(self._execute_map_function(map_function, item, i))
        
        # Execute with concurrency limit
        semaphore = None
        if self.max_concurrency and self.max_concurrency > 0:
            semaphore = asyncio.Semaphore(self.max_concurrency)
        
        if semaphore:
            async def limited_execute(coro):
                async with semaphore:
                    return await coro()
            results = await asyncio.gather(
                *[limited_execute(coro) for coro in coroutines],
                return_exceptions=True
            )
        else:
            results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    "item_index": i,
                    "item": collection[i],
                    "error": str(result)
                })
                
                if self.error_handling == "fail":
                    raise result
            else:
                successful_results.append({
                    "item_index": i,
                    "item": collection[i],
                    "result": result
                })
        
        self._parallel_results = {
            "mapped_results": successful_results,
            "failed_mappings": failed_results,
            "total_items": len(collection)
        }
        
        return {
            "result": successful_results,
            "parallel_results": self._parallel_results,
            "metadata": {
                "execution_mode": "map",
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "total_count": len(collection)
            }
        }
    
    async def _execute_task_with_function(self, task: dict[str, Any], index: int) -> dict[str, Any]:
        """Execute a task using the provided function."""
        task_data = {
            "task": task,
            "index": index
        }
        
        try:
            result = await self.task_function(task_data)
            return result
        except Exception as e:
            return e
    
    async def _execute_task_direct(self, task: dict[str, Any], index: int) -> dict[str, Any]:
        """Execute a task directly (for simple data tasks)."""
        # For simple tasks, just return the task data
        return {
            "task": task,
            "index": index,
            "executed_at": asyncio.get_event_loop().time()
        }
    
    async def _execute_map_function(self, map_function: Callable, item: Any, index: int) -> dict[str, Any]:
        """Execute map function on an item."""
        try:
            result = await map_function(item)
            return {
                "item": item,
                "index": index,
                "result": result,
                "executed_at": asyncio.get_event_loop().time()
            }
        except Exception as e:
            return {
                "item": item,
                "index": index,
                "error": str(e),
                "executed_at": asyncio.get_event_loop().time()
            }
    
    def set_execution_mode(self, execution_mode: str) -> None:
        """Change the execution mode dynamically."""
        if execution_mode.lower() in ["all", "any", "race", "map"]:
            self.execution_mode = execution_mode.lower()
            self._setup_required_inputs()
    
    def set_tasks(self, tasks: list[dict[str, Any]]) -> None:
        """Set the tasks to execute."""
        self.tasks = tasks
    
    def set_max_concurrency(self, max_concurrency: int) -> None:
        """Set maximum concurrent tasks."""
        self.max_concurrency = max_concurrency
    
    def set_timeout(self, timeout: float) -> None:
        """Set timeout for parallel execution."""
        self.timeout = timeout
    
    def get_parallel_info(self) -> dict[str, Any]:
        """Get information about the current parallel configuration."""
        return {
            "execution_mode": self.execution_mode,
            "max_concurrency": self.max_concurrency,
            "timeout": self.timeout,
            "error_handling": self.error_handling,
            "execution_count": self._execution_count,
            "tasks_configured": len(self.tasks) if self.tasks else 0
        }
    
    async def cleanup(self) -> None:
        """Cleanup parallel node resources."""
        self._execution_count = 0
        self._parallel_results = {}
        
        await super().cleanup()


class ParallelMapNode(ParallelNode):
    """Specialized node for parallel map operations."""
    
    def __init__(
        self,
        node_id: str = "parallel_map",
        map_function: Callable[[Any], dict[str, Any]] | None = None,
        max_concurrency: int | None = None,
        timeout: float | None = None,
        description: str = "Parallel map operation"
    ) -> None:
        super().__init__(
            node_id=node_id,
            execution_mode="map",
            map_function=map_function,
            max_concurrency=max_concurrency,
            timeout=timeout,
            description=description
        )


class ParallelAnyNode(ParallelNode):
    """Specialized node for parallel any (first success) operations."""
    
    def __init__(
        self,
        node_id: str = "parallel_any",
        tasks: list[dict[str, Any]] | None = None,
        timeout: float | None = None,
        max_concurrency: int | None = None,
        description: str = "Parallel any (first success) operation"
    ) -> None:
        super().__init__(
            node_id=node_id,
            execution_mode="any",
            tasks=tasks,
            timeout=timeout,
            max_concurrency=max_concurrency,
            description=description
        )


class ParallelRaceNode(ParallelNode):
    """Specialized node for parallel race operations."""
    
    def __init__(
        self,
        node_id: str = "parallel_race",
        tasks: list[dict[str, Any]] | None = None,
        timeout: float | None = None,
        max_concurrency: int | None = None,
        description: str = "Parallel race (first result) operation"
    ) -> None:
        super().__init__(
            node_id=node_id,
            execution_mode="race",
            tasks=tasks,
            timeout=timeout,
            max_concurrency=max_concurrency,
            description=description
        )
