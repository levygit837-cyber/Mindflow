"""Loop Node - Controls iterative execution in graphs.

This node implements various looping patterns including while loops,
for loops, and iterator-based loops with proper exit conditions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class LoopNode(StatefulNode, BaseNode):
    """Node that implements iterative execution patterns.
    
    This node supports multiple loop types:
    - While loops: Continue while condition is true
    - For loops: Iterate over a collection
    - Iterator loops: Continue until iterator is exhausted
    """
    
    def __init__(
        self,
        node_id: str = "loop",
        loop_type: str = "while",  # while, for, iterator, do_while
        condition: str | Callable[[dict[str, Any]], bool] | None = None,
        iterator: str | list | Callable | None = None,
        loop_body: Callable[[dict[str, Any], int], dict[str, Any]] | None = None,
        max_iterations: int | None = None,
        break_condition: str | Callable[[dict[str, Any]], bool] | None = None,
        continue_condition: str | Callable[[dict[str, Any]], bool] | None = None,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CONTROL,
            category=NodeCategory.CONTROL_FLOW,
            description=description or f"{loop_type} loop control"
        )
        
        self.loop_type = loop_type.lower()
        self.condition = condition
        self.iterator = iterator
        self.loop_body = loop_body
        self.max_iterations = max_iterations
        self.break_condition = break_condition
        self.continue_condition = continue_condition
        
        # Required inputs
        self._setup_required_inputs()
        self.config.outputs = {"result", "iterations", "loop_data", "metadata"}
        
        # Internal state
        self._iteration_count = 0
        self._loop_data = {}
        self._loop_complete = False
    
    def _setup_required_inputs(self) -> None:
        """Setup required inputs based on loop type."""
        if self.loop_type == "while":
            self.config.required_inputs = {"data", "condition"}
        elif self.loop_type == "for" or self.loop_type == "iterator":
            self.config.required_inputs = {"data", "iterator"}
        elif self.loop_type == "do_while":
            self.config.required_inputs = {"data", "condition"}
        else:
            self.config.required_inputs = {"data"}
    
    async def initialize(self) -> None:
        """Initialize the loop node."""
        await super().initialize()
        
        # Initialize loop-specific state
        self._iteration_count = 0
        self._loop_data = {}
        self._loop_complete = False
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the loop based on configured type."""
        data = state.get("data", {})
        
        try:
            if self.loop_type == "while":
                result = await self._execute_while_loop(data, state)
            elif self.loop_type == "for":
                result = await self._execute_for_loop(data, state)
            elif self.loop_type == "iterator":
                result = await self._execute_iterator_loop(data, state)
            elif self.loop_type == "do_while":
                result = await self._execute_do_while_loop(data, state)
            else:
                raise ValueError(f"Unsupported loop type: {self.loop_type}")
            
            return result
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("loop_node_execution_failed", 
                       loop_type=self.loop_type, 
                       error=str(e))
            
            return {
                "result": data,
                "iterations": self._iteration_count,
                "loop_data": self._loop_data,
                "error": str(e),
                "metadata": {"loop_type": self.loop_type, "status": "error"}
            }
    
    async def _execute_while_loop(self, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Execute a while loop."""
        if not self.loop_body:
            raise ValueError("Loop body function is required for while loop")
        
        loop_data = {"iterations": [], "current_iteration": 0}
        results = []
        
        while True:
            # Check break conditions
            if await self._should_break(data, loop_data):
                break
            
            # Check continue condition
            if await self._should_continue(data, loop_data):
                self._iteration_count += 1
                continue
            
            # Check max iterations
            if self.max_iterations and self._iteration_count >= self.max_iterations:
                break
            
            # Check loop condition
            if not await self._evaluate_condition(data, state):
                break
            
            # Execute loop body
            iteration_data = {
                "data": data,
                "iteration": self._iteration_count,
                "loop_data": loop_data
            }
            
            body_result = await self.loop_body(iteration_data)
            results.append(body_result)
            
            # Update loop data for next iteration
            loop_data.update(body_result.get("loop_data", {}))
            loop_data["current_iteration"] = self._iteration_count
            self._iteration_count += 1
        
        self._loop_complete = True
        self._loop_data = loop_data
        
        return {
            "result": results,
            "iterations": self._iteration_count,
            "loop_data": loop_data,
            "metadata": {
                "loop_type": "while",
                "completed_normally": self._loop_complete,
                "max_iterations_reached": self.max_iterations and self._iteration_count >= self.max_iterations
            }
        }
    
    async def _execute_for_loop(self, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Execute a for loop over a collection."""
        if not self.loop_body:
            raise ValueError("Loop body function is required for for loop")
        
        # Get iterator collection
        collection = await self._get_iterator_collection(data, state)
        if not collection:
            return {
                "result": [],
                "iterations": 0,
                "loop_data": {},
                "metadata": {"loop_type": "for", "status": "no_data"}
            }
        
        loop_data = {"iterations": [], "current_index": 0}
        results = []
        
        for index, item in enumerate(collection):
            # Check break conditions
            if await self._should_break(data, loop_data):
                break
            
            # Check continue condition
            if await self._should_continue(data, loop_data):
                continue
            
            # Check max iterations
            if self.max_iterations and self._iteration_count >= self.max_iterations:
                break
            
            # Prepare iteration data
            iteration_data = {
                "data": data,
                "item": item,
                "index": index,
                "loop_data": loop_data
            }
            
            # Execute loop body
            body_result = await self.loop_body(iteration_data)
            results.append(body_result)
            
            # Update loop data
            loop_data.update(body_result.get("loop_data", {}))
            loop_data["current_index"] = index + 1
            self._iteration_count += 1
        
        self._loop_complete = True
        self._loop_data = loop_data
        
        return {
            "result": results,
            "iterations": self._iteration_count,
            "loop_data": loop_data,
            "metadata": {
                "loop_type": "for",
                "collection_size": len(collection),
                "completed_normally": self._loop_complete
            }
        }
    
    async def _execute_iterator_loop(self, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Execute a loop using an iterator function."""
        if not self.loop_body:
            raise ValueError("Loop body function is required for iterator loop")
        
        if not callable(self.iterator):
            raise ValueError("Iterator must be callable for iterator loop")
        
        loop_data = {"iterations": [], "current_item": None}
        results = []
        
        while True:
            # Check break conditions
            if await self._should_break(data, loop_data):
                break
            
            # Check continue condition
            if await self._should_continue(data, loop_data):
                self._iteration_count += 1
                continue
            
            # Check max iterations
            if self.max_iterations and self._iteration_count >= self.max_iterations:
                break
            
            # Get next item from iterator
            try:
                iterator_result = self.iterator(data, loop_data)
            except StopIteration:
                break
            
            if not iterator_result:
                break
            
            # Prepare iteration data
            iteration_data = {
                "data": data,
                "item": iterator_result,
                "loop_data": loop_data
            }
            
            # Execute loop body
            body_result = await self.loop_body(iteration_data)
            results.append(body_result)
            
            # Update loop data
            loop_data.update(body_result.get("loop_data", {}))
            loop_data["current_item"] = iterator_result
            self._iteration_count += 1
        
        self._loop_complete = True
        self._loop_data = loop_data
        
        return {
            "result": results,
            "iterations": self._iteration_count,
            "loop_data": loop_data,
            "metadata": {
                "loop_type": "iterator",
                "completed_normally": self._loop_complete,
                "iterator_exhausted": True
            }
        }
    
    async def _execute_do_while_loop(self, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Execute a do-while loop (execute body, then check condition)."""
        if not self.loop_body:
            raise ValueError("Loop body function is required for do-while loop")
        
        loop_data = {"iterations": [], "current_iteration": 0}
        results = []
        
        while True:
            # Execute loop body first
            iteration_data = {
                "data": data,
                "iteration": self._iteration_count,
                "loop_data": loop_data
            }
            
            body_result = await self.loop_body(iteration_data)
            results.append(body_result)
            
            # Update loop data
            loop_data.update(body_result.get("loop_data", {}))
            loop_data["current_iteration"] = self._iteration_count
            self._iteration_count += 1
            
            # Check break conditions (after body execution)
            if await self._should_break(data, loop_data):
                break
            
            # Check continue condition
            if await self._should_continue(data, loop_data):
                self._iteration_count += 1
                continue
            
            # Check max iterations
            if self.max_iterations and self._iteration_count >= self.max_iterations:
                break
            
            # Check loop condition (at the end)
            if not await self._evaluate_condition(data, state):
                break
        
        self._loop_complete = True
        self._loop_data = loop_data
        
        return {
            "result": results,
            "iterations": self._iteration_count,
            "loop_data": loop_data,
            "metadata": {
                "loop_type": "do_while",
                "completed_normally": self._loop_complete,
                "executed_at_least_once": len(results) > 0
            }
        }
    
    async def _get_iterator_collection(self, data: dict[str, Any], state: dict[str, Any]) -> list[Any]:
        """Get the collection to iterate over."""
        if isinstance(self.iterator, str):
            # Field path in data
            field_path = self.iterator.split('.')
            collection = self._get_nested_value(data, field_path)
            return collection if isinstance(collection, list) else [collection]
        
        elif isinstance(self.iterator, list):
            # Static list
            return self.iterator
        
        elif callable(self.iterator):
            # Dynamic iterator function
            return self.iterator(data, state)
        
        return []
    
    async def _evaluate_condition(self, data: dict[str, Any], state: dict[str, Any]) -> bool:
        """Evaluate the loop condition."""
        if self.condition is None:
            return True  # Default to infinite loop
        
        if isinstance(self.condition, Callable):
            return self.condition(data)
        
        if isinstance(self.condition, str):
            # Use ConditionNode for string evaluation
            from mindflow_backend.nodes.implementations.control.condition_node import ConditionNode
            temp_node = ConditionNode(node_id="temp_condition", condition=self.condition)
            await temp_node.initialize()
            result = await temp_node._evaluate_condition(data)
            await temp_node.cleanup()
            return result
        
        return bool(self.condition)
    
    async def _should_break(self, data: dict[str, Any], loop_data: dict[str, Any]) -> bool:
        """Check if loop should break."""
        if not self.break_condition:
            return False
        
        if isinstance(self.break_condition, Callable):
            return self.break_condition(data, loop_data)
        
        if isinstance(self.break_condition, str):
            # Use ConditionNode for string evaluation
            from mindflow_backend.nodes.implementations.control.condition_node import ConditionNode
            temp_node = ConditionNode(node_id="temp_break", condition=self.break_condition)
            await temp_node.initialize()
            result = await temp_node._evaluate_condition(data)
            await temp_node.cleanup()
            return result
        
        return False
    
    async def _should_continue(self, data: dict[str, Any], loop_data: dict[str, Any]) -> bool:
        """Check if loop should continue to next iteration."""
        if not self.continue_condition:
            return False
        
        if isinstance(self.continue_condition, Callable):
            return self.continue_condition(data, loop_data)
        
        if isinstance(self.continue_condition, str):
            # Use ConditionNode for string evaluation
            from mindflow_backend.nodes.implementations.control.condition_node import ConditionNode
            temp_node = ConditionNode(node_id="temp_continue", condition=self.continue_condition)
            await temp_node.initialize()
            result = await temp_node._evaluate_condition(data)
            await temp_node.cleanup()
            return result
        
        return False
    
    def _get_nested_value(self, data: dict[str, Any], path: str) -> Any:
        """Get nested value from data using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def set_loop_type(self, loop_type: str) -> None:
        """Change the loop type dynamically."""
        if loop_type.lower() in ["while", "for", "iterator", "do_while"]:
            self.loop_type = loop_type.lower()
            self._setup_required_inputs()
    
    def set_max_iterations(self, max_iterations: int) -> None:
        """Set maximum number of iterations."""
        self.max_iterations = max_iterations
    
    def get_loop_info(self) -> dict[str, Any]:
        """Get information about the current loop configuration."""
        return {
            "loop_type": self.loop_type,
            "max_iterations": self.max_iterations,
            "current_iteration_count": self._iteration_count,
            "loop_complete": self._loop_complete,
            "has_condition": self.condition is not None,
            "has_break_condition": self.break_condition is not None,
            "has_continue_condition": self.continue_condition is not None
        }
    
    async def cleanup(self) -> None:
        """Cleanup loop node resources."""
        self._iteration_count = 0
        self._loop_data = {}
        self._loop_complete = False
        
        await super().cleanup()


class ForEachNode(LoopNode):
    """Specialized node for forEach-style iteration."""
    
    def __init__(
        self,
        node_id: str = "for_each",
        collection_path: str = "items",
        item_name: str = "item",
        loop_body: Callable[[dict[str, Any], int], dict[str, Any]] | None = None,
        max_iterations: int | None = None,
        description: str = "For each loop over collection"
    ) -> None:
        # Create iterator that extracts collection from data
        iterator = lambda data, loop_data: self._get_nested_value(data, collection_path)
        
        # Create loop body that includes item in loop data
        def enhanced_loop_body(loop_data):
            item = loop_data.get(item_name)
            if loop_body and item is not None:
                return loop_body(loop_data)
            return {"loop_data": loop_data}
        
        super().__init__(
            node_id=node_id,
            loop_type="for",
            iterator=iterator,
            loop_body=enhanced_loop_body,
            max_iterations=max_iterations,
            description=description
        )
        
        self.collection_path = collection_path
        self.item_name = item_name


class WhileNode(LoopNode):
    """Specialized node for while loops."""
    
    def __init__(
        self,
        node_id: str = "while_loop",
        condition: str | Callable[[dict[str, Any]], bool] = None,
        loop_body: Callable[[dict[str, Any], int], dict[str, Any]] | None = None,
        max_iterations: int | None = None,
        description: str = "While loop with condition check"
    ) -> None:
        super().__init__(
            node_id=node_id,
            loop_type="while",
            condition=condition,
            loop_body=loop_body,
            max_iterations=max_iterations,
            description=description
        )


class DoWhileNode(LoopNode):
    """Specialized node for do-while loops."""
    
    def __init__(
        self,
        node_id: str = "do_while_loop",
        condition: str | Callable[[dict[str, Any]], bool] = None,
        loop_body: Callable[[dict[str, Any], int], dict[str, Any]] | None = None,
        max_iterations: int | None = None,
        description: str = "Do-while loop (execute then check)"
    ) -> None:
        super().__init__(
            node_id=node_id,
            loop_type="do_while",
            condition=condition,
            loop_body=loop_body,
            max_iterations=max_iterations,
            description=description
        )
