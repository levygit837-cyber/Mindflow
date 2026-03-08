"""Condition Node - Controls conditional flow in graphs.

This node evaluates conditions and directs flow based on results,
enabling complex decision trees and conditional branching logic.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class ConditionNode(StatefulNode, BaseNode):
    """Node that evaluates conditions and directs flow.
    
    This node implements conditional logic, allowing the graph to branch
    based on data values, expressions, or custom evaluation functions.
    """
    
    def __init__(
        self,
        node_id: str = "condition",
        condition: Union[str, Callable[[Dict[str, Any]], bool]] = None,
        true_path: Optional[str] = None,
        false_path: Optional[str] = None,
        default_path: Optional[str] = None,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.CONTROL,
            category=NodeCategory.CONTROL_FLOW,
            description=description or "Conditional flow control"
        )
        
        self.condition = condition
        self.true_path = true_path
        self.false_path = false_path
        self.default_path = default_path
        
        # Required inputs
        self.config.required_inputs = {"data"}
        self.config.outputs = {"result", "condition_met", "next_path"}
        
        # Internal state
        self._condition_cache = {}
        self._evaluation_count = 0
    
    async def initialize(self) -> None:
        """Initialize the condition node."""
        await super().initialize()
        
        # Pre-compile string conditions for performance
        if isinstance(self.condition, str):
            self._compile_string_condition(self.condition)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the condition evaluation and return path decision."""
        data = state.get("data", {})
        
        try:
            # Evaluate condition
            condition_result = await self._evaluate_condition(data)
            
            # Determine next path
            next_path = self._determine_next_path(condition_result)
            
            self._evaluation_count += 1
            
            return {
                "result": data,
                "condition_met": condition_result,
                "next_path": next_path,
                "evaluation_metadata": {
                    "evaluation_count": self._evaluation_count,
                    "condition_type": type(self.condition).__name__,
                    "execution_time": 0.0  # Would be measured in real implementation
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("condition_node_execution_failed", error=str(e))
            
            return {
                "result": data,
                "condition_met": False,
                "next_path": self.default_path or "error",
                "error": str(e)
            }
    
    async def _evaluate_condition(self, data: Dict[str, Any]) -> bool:
        """Evaluate the condition against the provided data."""
        if self.condition is None:
            return True  # Default to true if no condition
        
        if isinstance(self.condition, Callable):
            # Custom evaluation function
            return self.condition(data)
        
        if isinstance(self.condition, str):
            # String-based condition evaluation
            return await self._evaluate_string_condition(data, self.condition)
        
        # Direct boolean value
        return bool(self.condition)
    
    async def _evaluate_string_condition(self, data: Dict[str, Any], condition_str: str) -> bool:
        """Evaluate a string-based condition."""
        # Check cache first
        if condition_str in self._condition_cache:
            return self._condition_cache[condition_str](data)
        
        # Parse and compile condition
        eval_function = self._parse_and_compile_condition(condition_str)
        
        # Cache for future use
        self._condition_cache[condition_str] = eval_function
        
        # Evaluate condition
        return eval_function(data)
    
    def _parse_and_compile_condition(self, condition_str: str) -> Callable[[Dict[str, Any]], bool]:
        """Parse condition string and compile to executable function."""
        # Simple condition language parser
        # Supports syntax like: "data.age > 18", "data.status == 'active'", etc.
        
        try:
            # Extract field path and operator
            if ">" in condition_str:
                field, value = condition_str.split(">", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) > value
            
            elif "<" in condition_str:
                field, value = condition_str.split("<", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) < value
            
            elif "==" in condition_str:
                field, value = condition_str.split("==", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) == value
            
            elif "!=" in condition_str:
                field, value = condition_str.split("!=", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) != value
            
            elif "in" in condition_str:
                field, value = condition_str.split("in", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) in value
            
            elif "not in" in condition_str:
                field, value = condition_str.split("not in", 1)
                field = field.strip()
                value = self._parse_value(value.strip())
                return lambda data: self._get_nested_value(data, field) not in value
            
            elif "exists" in condition_str:
                field = condition_str.replace("exists", "").strip()
                return lambda data: self._get_nested_value(data, field) is not None
            
            elif "not exists" in condition_str:
                field = condition_str.replace("not exists", "").strip()
                return lambda data: self._get_nested_value(data, field) is None
            
            else:
                # Default to truthiness of field value
                field = condition_str.strip()
                return lambda data: bool(self._get_nested_value(data, field))
                
        except Exception:
            # If parsing fails, default to False
            return lambda data: False
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from data using dot notation."""
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse a value string to appropriate type."""
        value_str = value_str.strip()
        
        # Remove quotes if present
        if (value_str.startswith('"') and value_str.endswith('"')) or \
           (value_str.startswith("'") and value_str.endswith("'")):
            return value_str[1:-1]
        
        # Try to parse as number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        
        # Return as string
        return value_str
    
    def _determine_next_path(self, condition_result: bool) -> Optional[str]:
        """Determine the next path based on condition result."""
        if condition_result and self.true_path:
            return self.true_path
        elif not condition_result and self.false_path:
            return self.false_path
        elif self.default_path:
            return self.default_path
        
        # No explicit path configured
        return None
    
    def _compile_string_condition(self, condition_str: str) -> None:
        """Pre-compile string condition for performance."""
        # This would implement more sophisticated parsing and caching
        # For now, just store the string for later parsing
        pass
    
    def set_condition(self, condition: Union[str, Callable[[Dict[str, Any]], bool]]) -> None:
        """Update the condition dynamically."""
        self.condition = condition
        
        # Clear cache if condition changed
        if isinstance(condition, str):
            self._condition_cache.clear()
    
    def set_paths(
        self,
        true_path: Optional[str] = None,
        false_path: Optional[str] = None,
        default_path: Optional[str] = None
    ) -> None:
        """Update the path configurations."""
        if true_path is not None:
            self.true_path = true_path
        if false_path is not None:
            self.false_path = false_path
        if default_path is not None:
            self.default_path = default_path
    
    def get_condition_info(self) -> Dict[str, Any]:
        """Get information about the current condition configuration."""
        return {
            "condition_type": type(self.condition).__name__,
            "condition_str": str(self.condition) if isinstance(self.condition, str) else None,
            "true_path": self.true_path,
            "false_path": self.false_path,
            "default_path": self.default_path,
            "evaluation_count": self._evaluation_count,
            "cache_size": len(self._condition_cache)
        }
    
    def clear_cache(self) -> None:
        """Clear the condition evaluation cache."""
        self._condition_cache.clear()
    
    async def cleanup(self) -> None:
        """Cleanup condition node resources."""
        self._condition_cache.clear()
        self._evaluation_count = 0
        
        await super().cleanup()


class MultiConditionNode(ConditionNode):
    """Node that evaluates multiple conditions with logical operators."""
    
    def __init__(
        self,
        node_id: str = "multi_condition",
        conditions: List[Dict[str, Any]] = None,
        operator: str = "and",  # and, or, xor
        description: str = "Multiple condition evaluation"
    ) -> None:
        # Initialize with a custom condition that handles multiple conditions
        multi_condition = self._create_multi_condition_evaluator(conditions, operator)
        
        super().__init__(
            node_id=node_id,
            condition=multi_condition,
            description=description
        )
        
        self.conditions = conditions or []
        self.operator = operator.lower()
    
    def _create_multi_condition_evaluator(
        self,
        conditions: List[Dict[str, Any]],
        operator: str
    ) -> Callable[[Dict[str, Any]], bool]:
        """Create a function that evaluates multiple conditions."""
        async def multi_evaluator(data: Dict[str, Any]) -> bool:
            results = []
            
            for condition_config in conditions:
                condition_str = condition_config.get("condition", "")
                condition_value = condition_config.get("value", True)
                
                # Parse individual condition
                if isinstance(condition_str, str):
                    # Create temporary ConditionNode for evaluation
                    temp_node = ConditionNode(
                        node_id="temp",
                        condition=condition_str
                    )
                    await temp_node.initialize()
                    result = await temp_node._evaluate_condition(data)
                    await temp_node.cleanup()
                else:
                    result = bool(condition_value)
                
                results.append(result)
            
            # Apply logical operator
            if operator == "and":
                return all(results)
            elif operator == "or":
                return any(results)
            elif operator == "xor":
                return sum(results) == 1
            else:
                # Default to and
                return all(results)
        
        return multi_evaluator
    
    def add_condition(self, condition_str: str, value: Any = True) -> None:
        """Add a new condition to the multi-condition node."""
        self.conditions.append({
            "condition": condition_str,
            "value": value
        })
        
        # Update the multi-condition evaluator
        self.condition = self._create_multi_condition_evaluator(self.conditions, self.operator)
        
        # Clear cache since conditions changed
        self.clear_cache()
    
    def remove_condition(self, index: int) -> bool:
        """Remove a condition by index."""
        if 0 <= index < len(self.conditions):
            self.conditions.pop(index)
            
            # Update the multi-condition evaluator
            self.condition = self._create_multi_condition_evaluator(self.conditions, self.operator)
            
            # Clear cache since conditions changed
            self.clear_cache()
            return True
        
        return False
    
    def get_conditions_info(self) -> Dict[str, Any]:
        """Get information about all configured conditions."""
        return {
            "conditions": self.conditions,
            "operator": self.operator,
            "total_conditions": len(self.conditions)
        }
