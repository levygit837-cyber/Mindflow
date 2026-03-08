"""Transform Node - Transforms data in processing pipelines.

This node applies transformation functions to data, supporting
various transformation patterns and data manipulation operations.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class TransformNode(StatefulNode, BaseNode):
    """Node that transforms data using configurable functions.
    
    This node supports various transformation patterns:
    - Function transform: Apply custom function to data
    - Mapping transform: Map values using key-value pairs
    - Filter transform: Filter data based on conditions
    - Aggregate transform: Aggregate data using operations
    """
    
    def __init__(
        self,
        node_id: str = "transform",
        transform_type: str = "function",  # function, mapping, filter, aggregate
        transform_function: Optional[Callable[[Any], Any]] = None,
        mapping_rules: Optional[Dict[str, Any]] = None,
        filter_condition: Optional[Union[str, Callable[[Any], bool]]] = None,
        aggregate_operation: Optional[str] = None,  # sum, count, avg, min, max, custom
        aggregate_function: Optional[Callable[[List[Any]], Any]] = None,
        field_path: Optional[str] = None,
        preserve_structure: bool = True,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.PROCESSING,
            description=description or f"{transform_type} transform"
        )
        
        self.transform_type = transform_type.lower()
        self.transform_function = transform_function
        self.mapping_rules = mapping_rules or {}
        self.filter_condition = filter_condition
        self.aggregate_operation = aggregate_operation
        self.aggregate_function = aggregate_function
        self.field_path = field_path
        self.preserve_structure = preserve_structure
        
        # Required inputs
        self.config.required_inputs = {"data"}
        self.config.outputs = {"result", "transformed_data", "metadata"}
        
        # Internal state
        self._transformation_count = 0
        self._transformation_history = []
    
    async def initialize(self) -> None:
        """Initialize the transform node."""
        await super().initialize()
        
        # Pre-compile filter conditions for performance
        if isinstance(self.filter_condition, str):
            self._compile_filter_condition(self.filter_condition)
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the transformation based on configured type."""
        data = state.get("data", {})
        
        try:
            # Extract field if specified
            if self.field_path:
                data = self._extract_field_data(data, self.field_path)
            
            # Apply transformation based on type
            if self.transform_type == "function":
                result = await self._apply_function_transform(data, state)
            elif self.transform_type == "mapping":
                result = await self._apply_mapping_transform(data, state)
            elif self.transform_type == "filter":
                result = await self._apply_filter_transform(data, state)
            elif self.transform_type == "aggregate":
                result = await self._apply_aggregate_transform(data, state)
            else:
                raise ValueError(f"Unsupported transform type: {self.transform_type}")
            
            self._transformation_count += 1
            
            return {
                "result": result,
                "transformed_data": result,
                "metadata": {
                    "transform_type": self.transform_type,
                    "transformation_count": self._transformation_count,
                    "field_path": self.field_path,
                    "preserve_structure": self.preserve_structure
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("transform_node_execution_failed", 
                       transform_type=self.transform_type, 
                       error=str(e))
            
            return {
                "result": data,
                "transformed_data": data,
                "error": str(e),
                "metadata": {"transform_type": self.transform_type, "status": "error"}
            }
    
    async def _apply_function_transform(self, data: Any, state: Dict[str, Any]) -> Any:
        """Apply custom function transformation."""
        if not self.transform_function:
            raise ValueError("Transform function is required for function transform")
        
        # Handle different data structures
        if isinstance(data, list):
            return [await self.transform_function(item) for item in data]
        elif isinstance(data, dict):
            return {key: await self.transform_function(value) for key, value in data.items()}
        else:
            return await self.transform_function(data)
    
    async def _apply_mapping_transform(self, data: Any, state: Dict[str, Any]) -> Any:
        """Apply mapping transformation to data."""
        if not self.mapping_rules:
            return data
        
        # Handle different data structures
        if isinstance(data, list):
            return [self._map_item(item, self.mapping_rules) for item in data]
        elif isinstance(data, dict):
            return {key: self._map_item(value, self.mapping_rules) for key, value in data.items()}
        else:
            return self._map_item(data, self.mapping_rules)
    
    def _map_item(self, item: Any, mapping_rules: Dict[str, Any]) -> Any:
        """Map a single item using the mapping rules."""
        if isinstance(item, dict):
            mapped_item = {}
            for key, value in item.items():
                if key in mapping_rules:
                    mapped_item[key] = self._apply_mapping_rule(value, mapping_rules[key])
                else:
                    mapped_item[key] = value
            return mapped_item
        else:
            if "default" in mapping_rules:
                return self._apply_mapping_rule(item, mapping_rules["default"])
            return item
    
    def _apply_mapping_rule(self, value: Any, rule: Any) -> Any:
        """Apply a single mapping rule."""
        if isinstance(rule, dict):
            # Complex rule with conditions
            if "conditions" in rule and "transform" in rule:
                for condition in rule["conditions"]:
                    if self._evaluate_mapping_condition(value, condition):
                        return self._apply_mapping_rule(value, rule["transform"])
            return value
        elif callable(rule):
            return rule(value)
        else:
            # Simple value replacement
            return rule
    
    def _evaluate_mapping_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a mapping condition."""
        field = condition.get("field")
        operator = condition.get("operator", "==")
        expected = condition.get("value")
        
        if not isinstance(value, dict) or field not in value:
            return False
        
        actual_value = value[field]
        
        if operator == "==":
            return actual_value == expected
        elif operator == "!=":
            return actual_value != expected
        elif operator == ">":
            return actual_value > expected
        elif operator == "<":
            return actual_value < expected
        elif operator == "in":
            return actual_value in expected
        elif operator == "not_in":
            return actual_value not in expected
        
        return False
    
    async def _apply_filter_transform(self, data: Any, state: Dict[str, Any]) -> Any:
        """Apply filter transformation to data."""
        if not self.filter_condition:
            return data
        
        # Handle different data structures
        if isinstance(data, list):
            filtered_data = []
            for item in data:
                if await self._evaluate_filter_condition(item):
                    filtered_data.append(item)
            return filtered_data
        elif isinstance(data, dict):
            filtered_data = {}
            for key, value in data.items():
                if await self._evaluate_filter_condition(value):
                    filtered_data[key] = value
            return filtered_data
        else:
            # Single item
            return data if await self._evaluate_filter_condition(data) else None
    
    async def _evaluate_filter_condition(self, item: Any) -> bool:
        """Evaluate filter condition for an item."""
        if isinstance(self.filter_condition, Callable):
            return self.filter_condition(item)
        
        if isinstance(self.filter_condition, str):
            # Use ConditionNode for string evaluation
            from mindflow_backend.nodes.implementations.control.condition_node import ConditionNode
            temp_node = ConditionNode(node_id="temp_filter", condition=self.filter_condition)
            await temp_node.initialize()
            result = await temp_node._evaluate_condition({"data": item})
            await temp_node.cleanup()
            return result
        
        return bool(self.filter_condition)
    
    async def _apply_aggregate_transform(self, data: Any, state: Dict[str, Any]) -> Any:
        """Apply aggregate transformation to data."""
        if not data:
            return None
        
        # Convert to list for aggregation
        if isinstance(data, dict):
            data = list(data.values())
        elif not isinstance(data, list):
            data = [data]
        
        if not data:
            return None
        
        # Apply custom aggregate function
        if self.aggregate_function:
            return await self.aggregate_function(data)
        
        # Apply built-in aggregate operations
        if self.aggregate_operation == "sum":
            return sum(data)
        elif self.aggregate_operation == "count":
            return len(data)
        elif self.aggregate_operation == "avg":
            return sum(data) / len(data) if data else 0
        elif self.aggregate_operation == "min":
            return min(data) if data else None
        elif self.aggregate_operation == "max":
            return max(data) if data else None
        elif self.aggregate_operation == "first":
            return data[0] if data else None
        elif self.aggregate_operation == "last":
            return data[-1] if data else None
        elif self.aggregate_operation == "unique":
            return list(set(data))
        else:
            raise ValueError(f"Unsupported aggregate operation: {self.aggregate_operation}")
    
    def _extract_field_data(self, data: Any, field_path: str) -> Any:
        """Extract data from nested field path."""
        if not isinstance(data, dict):
            return data
        
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _compile_filter_condition(self, condition_str: str) -> None:
        """Pre-compile filter condition for performance."""
        # This would implement more sophisticated parsing and caching
        pass
    
    def set_transform_function(self, transform_function: Callable) -> None:
        """Set the transform function dynamically."""
        self.transform_type = "function"
        self.transform_function = transform_function
    
    def set_mapping_rules(self, mapping_rules: Dict[str, Any]) -> None:
        """Set mapping rules dynamically."""
        self.transform_type = "mapping"
        self.mapping_rules = mapping_rules
    
    def set_filter_condition(self, filter_condition: Union[str, Callable]) -> None:
        """Set filter condition dynamically."""
        self.transform_type = "filter"
        self.filter_condition = filter_condition
    
    def set_aggregate_operation(self, operation: str, function: Optional[Callable] = None) -> None:
        """Set aggregate operation dynamically."""
        self.transform_type = "aggregate"
        self.aggregate_operation = operation
        self.aggregate_function = function
    
    def get_transform_info(self) -> Dict[str, Any]:
        """Get information about the current transform configuration."""
        return {
            "transform_type": self.transform_type,
            "transformation_count": self._transformation_count,
            "has_function": self.transform_function is not None,
            "has_mapping": len(self.mapping_rules) > 0,
            "has_filter": self.filter_condition is not None,
            "has_aggregate": self.aggregate_operation is not None,
            "field_path": self.field_path,
            "preserve_structure": self.preserve_structure
        }
    
    async def cleanup(self) -> None:
        """Cleanup transform node resources."""
        self._transformation_count = 0
        self._transformation_history = []
        
        await super().cleanup()


class DataMappingNode(TransformNode):
    """Specialized node for data mapping operations."""
    
    def __init__(
        self,
        node_id: str = "data_mapping",
        mapping_rules: Dict[str, Any],
        field_mappings: Optional[Dict[str, str]] = None,
        description: str = "Data mapping transformation"
    ) -> None:
        super().__init__(
            node_id=node_id,
            transform_type="mapping",
            mapping_rules=mapping_rules,
            description=description
        )
        
        self.field_mappings = field_mappings or {}
    
    def apply_field_mappings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field name mappings to data."""
        if not self.field_mappings:
            return data
        
        mapped_data = {}
        for old_field, new_field in self.field_mappings.items():
            if old_field in data:
                mapped_data[new_field] = data[old_field]
            else:
                mapped_data[old_field] = data.get(old_field)
        
        return mapped_data


class DataValidationNode(TransformNode):
    """Specialized node for data validation and transformation."""
    
    def __init__(
        self,
        node_id: str = "data_validation",
        validation_rules: List[Dict[str, Any]],
        strict_mode: bool = False,
        description: str = "Data validation transformation"
    ) -> None:
        # Create validation function
        def validation_function(data):
            results = []
            is_valid = True
            
            for rule in validation_rules:
                field = rule.get("field")
                required = rule.get("required", False)
                data_type = rule.get("type")
                min_value = rule.get("min")
                max_value = rule.get("max")
                pattern = rule.get("pattern")
                
                field_value = data.get(field) if isinstance(data, dict) else data
                
                # Check required
                if required and field_value is None:
                    is_valid = False
                    results.append(f"Field {field} is required")
                    continue
                
                # Check type
                if data_type and not self._check_type(field_value, data_type):
                    is_valid = False
                    results.append(f"Field {field} must be {data_type}")
                    continue
                
                # Check range
                if min_value is not None and field_value < min_value:
                    is_valid = False
                    results.append(f"Field {field} must be >= {min_value}")
                    continue
                
                if max_value is not None and field_value > max_value:
                    is_valid = False
                    results.append(f"Field {field} must be <= {max_value}")
                    continue
                
                # Check pattern
                if pattern and not self._check_pattern(field_value, pattern):
                    is_valid = False
                    results.append(f"Field {field} does not match pattern {pattern}")
                    continue
            
            return {
                "is_valid": is_valid,
                "results": results,
                "data": data
            }
        
        super().__init__(
            node_id=node_id,
            transform_type="function",
            transform_function=validation_function,
            description=description
        )
        
        self.validation_rules = validation_rules
        self.strict_mode = strict_mode
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        
        return True
    
    def _check_pattern(self, value: Any, pattern: str) -> bool:
        """Check if value matches regex pattern."""
        import re
        try:
            return bool(re.search(pattern, str(value)))
        except re.error:
            return False
