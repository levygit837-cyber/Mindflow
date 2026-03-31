"""Filter Node - Filters data in processing pipelines.

This node filters data based on various criteria including
field values, conditions, and custom filter functions.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class FilterNode(StatefulNode, BaseNode):
    """Node that filters data based on configurable criteria.
    
    This node supports various filter types:
    - Field filter: Filter by field existence/values
    - Condition filter: Filter by custom conditions
    - Range filter: Filter by numeric ranges
    - Set filter: Filter by membership in sets
    - Pattern filter: Filter by regex patterns
    """
    
    def __init__(
        self,
        node_id: str = "filter",
        filter_type: str = "field",  # field, condition, range, set, pattern
        filter_config: dict[str, Any] | None = None,
        filter_function: Callable[[Any], bool] | None = None,
        field_path: str | None = None,
        include_empty: bool = False,
        case_sensitive: bool = True,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.PROCESSING,
            description=description or f"{filter_type} filter"
        )
        
        self.filter_type = filter_type.lower()
        self.filter_config = filter_config or {}
        self.filter_function = filter_function
        self.field_path = field_path
        self.include_empty = include_empty
        self.case_sensitive = case_sensitive
        
        # Required inputs
        self.config.required_inputs = {"data"}
        self.config.outputs = {"result", "filtered_data", "metadata"}
        
        # Internal state
        self._filter_count = 0
        self._filter_cache = {}
    
    async def initialize(self) -> None:
        """Initialize the filter node."""
        await super().initialize()
        
        # Pre-compile filter conditions for performance
        if self.filter_type in ["condition", "pattern"]:
            self._compile_filter_conditions()
    
    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the filter based on configured type."""
        data = state.get("data", {})
        
        try:
            # Extract field if specified
            if self.field_path:
                data = self._extract_field_data(data, self.field_path)
            
            # Apply filter based on type
            if self.filter_type == "field":
                result = await self._apply_field_filter(data)
            elif self.filter_type == "condition":
                result = await self._apply_condition_filter(data)
            elif self.filter_type == "range":
                result = await self._apply_range_filter(data)
            elif self.filter_type == "set":
                result = await self._apply_set_filter(data)
            elif self.filter_type == "pattern":
                result = await self._apply_pattern_filter(data)
            elif self.filter_type == "custom":
                result = await self._apply_custom_filter(data)
            else:
                raise ValueError(f"Unsupported filter type: {self.filter_type}")
            
            self._filter_count += 1
            
            return {
                "result": result,
                "filtered_data": result,
                "metadata": {
                    "filter_type": self.filter_type,
                    "filter_count": self._filter_count,
                    "input_count": self._count_input_items(data),
                    "output_count": len(result) if isinstance(result, list) else 1
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("filter_node_execution_failed", 
                       filter_type=self.filter_type, 
                       error=str(e))
            
            return {
                "result": data,
                "filtered_data": data,
                "error": str(e),
                "metadata": {"filter_type": self.filter_type, "status": "error"}
            }
    
    async def _apply_field_filter(self, data: Any) -> Any:
        """Apply field-based filtering."""
        if not self.filter_config:
            return data
        
        # Handle different data structures
        if isinstance(data, list):
            return await self._filter_list(data)
        elif isinstance(data, dict):
            return await self._filter_dict(data)
        else:
            # Single item
            return data if self._passes_field_filter(data) else None
    
    async def _filter_list(self, data: list[Any]) -> list[Any]:
        """Filter a list based on field criteria."""
        filtered = []
        
        for item in data:
            if self._passes_field_filter(item):
                filtered.append(item)
        
        return filtered
    
    async def _filter_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter a dictionary based on field criteria."""
        filtered = {}
        
        for key, value in data.items():
            if self._passes_field_filter({key: value}):
                filtered[key] = value
        
        return filtered
    
    def _passes_field_filter(self, item: Any) -> bool:
        """Check if an item passes field filter criteria."""
        # Check include_empty setting
        if not self.include_empty and self._is_empty_value(item):
            return False
        
        # Apply field filters from config
        for field, criteria in self.filter_config.items():
            if not self._check_field_criteria(item, field, criteria):
                return False
        
        return True
    
    def _is_empty_value(self, value: Any) -> bool:
        """Check if value is considered empty."""
        return value is None or value == "" or value == []
    
    async def _apply_condition_filter(self, data: Any) -> Any:
        """Apply condition-based filtering."""
        if not self.filter_function:
            return data
        
        # Handle different data structures
        if isinstance(data, list):
            return [item for item in data if self.filter_function(item)]
        elif isinstance(data, dict):
            return {key: value for key, value in data.items() if self.filter_function({key: value})}
        else:
            return data if self.filter_function(data) else None
    
    async def _apply_range_filter(self, data: Any) -> Any:
        """Apply range-based filtering."""
        if not self.filter_config:
            return data
        
        field = self.filter_config.get("field")
        min_val = self.filter_config.get("min")
        max_val = self.filter_config.get("max")
        
        if not field or min_val is None or max_val is None:
            return data
        
        # Extract field value
        field_value = self._get_field_value(data, field)
        if field_value is None:
            return None
        
        # Check range
        if not self._is_numeric(field_value):
            return None
        
        passes_min = min_val is None or field_value >= min_val
        passes_max = max_val is None or field_value <= max_val
        
        return data if passes_min and passes_max else None
    
    async def _apply_set_filter(self, data: Any) -> Any:
        """Apply set-based filtering."""
        if not self.filter_config:
            return data
        
        field = self.filter_config.get("field")
        allowed_values = self.filter_config.get("values", set())
        
        if not field or not allowed_values:
            return data
        
        # Extract field value
        field_value = self._get_field_value(data, field)
        if field_value is None:
            return None
        
        # Check membership
        return data if field_value in allowed_values else None
    
    async def _apply_pattern_filter(self, data: Any) -> Any:
        """Apply regex pattern-based filtering."""
        if not self.filter_config:
            return data
        
        field = self.filter_config.get("field")
        pattern = self.filter_config.get("pattern")
        
        if not field or not pattern:
            return data
        
        # Extract field value
        field_value = self._get_field_value(data, field)
        if field_value is None:
            return None
        
        # Apply regex pattern
        import re
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE if not self.case_sensitive else 0)
            return data if compiled_pattern.search(str(field_value)) else None
        except re.error:
            return None
    
    async def _apply_custom_filter(self, data: Any) -> Any:
        """Apply custom filter function."""
        if not self.filter_function:
            return data
        
        # Handle different data structures
        if isinstance(data, list):
            return [item for item in data if self.filter_function(item)]
        elif isinstance(data, dict):
            return {key: value for key, value in data.items() if self.filter_function({key: value})}
        else:
            return data if self.filter_function(data) else None
    
    def _get_field_value(self, data: Any, field: str) -> Any:
        """Get field value from data using dot notation."""
        if isinstance(data, dict):
            keys = field.split('.')
            current = data
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current
        
        return None
    
    def _is_numeric(self, value: Any) -> bool:
        """Check if value is numeric."""
        return isinstance(value, (int, float))
    
    def _extract_field_data(self, data: Any, field_path: str) -> Any:
        """Extract data from field path."""
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
    
    def _count_input_items(self, data: Any) -> int:
        """Count the number of items in input data."""
        if isinstance(data, list) or isinstance(data, dict):
            return len(data)
        elif data is not None:
            return 1
        else:
            return 0
    
    def _compile_filter_conditions(self) -> None:
        """Pre-compile filter conditions for performance."""
        # This would implement more sophisticated parsing and caching
        pass
    
    def set_filter_config(self, filter_config: dict[str, Any]) -> None:
        """Update filter configuration."""
        self.filter_config = filter_config
        
        # Clear cache if filter changed
        if self.filter_type in ["condition", "pattern"]:
            self._filter_cache.clear()
    
    def set_filter_function(self, filter_function: Callable[[Any], bool]) -> None:
        """Set custom filter function."""
        self.filter_type = "custom"
        self.filter_function = filter_function
    
    def get_filter_info(self) -> dict[str, Any]:
        """Get information about current filter configuration."""
        return {
            "filter_type": self.filter_type,
            "filter_config": self.filter_config,
            "filter_count": self._filter_count,
            "field_path": self.field_path,
            "include_empty": self.include_empty,
            "case_sensitive": self.case_sensitive,
            "cache_size": len(self._filter_cache)
        }
    
    def clear_cache(self) -> None:
        """Clear filter condition cache."""
        self._filter_cache.clear()
    
    async def cleanup(self) -> None:
        """Cleanup filter node resources."""
        self._filter_count = 0
        self._filter_cache.clear()
        
        await super().cleanup()


class MultiFilterNode(FilterNode):
    """Node that applies multiple filters in sequence."""
    
    def __init__(
        self,
        node_id: str = "multi_filter",
        filters: list[dict[str, Any]] = None,
        operator: str = "and",  # and, or, xor
        description: str = "Multiple filter application"
    ) -> None:
        super().__init__(
            node_id=node_id,
            filter_type="custom",
            description=description
        )
        
        self.filters = filters or []
        self.operator = operator.lower()
        
        # Create combined filter function
        self.filter_function = self._create_combined_filter(self.filters, self.operator)
    
    def _create_combined_filter(
        self,
        filters: list[dict[str, Any]],
        operator: str
    ) -> Callable[[Any], bool]:
        """Create a combined filter function from multiple filters."""
        async def combined_filter(item) -> bool:
            results = []
            
            for filter_config in filters:
                filter_type = filter_config.get("type", "field")
                filter_specific_config = filter_config.get("config", {})
                
                # Create temporary filter node
                temp_filter = FilterNode(
                    node_id=f"temp_{filter_type}",
                    filter_type=filter_type,
                    filter_config=filter_specific_config
                )
                
                # Apply filter
                passes = await temp_filter._apply_filter_by_type(item, filter_type, filter_specific_config)
                results.append(passes)
                
                await temp_filter.cleanup()
            
            # Apply logical operator
            if operator == "and":
                return all(results)
            elif operator == "or":
                return any(results)
            elif operator == "xor":
                return sum(results) == 1
            else:
                return all(results)
        
        return combined_filter
    
    async def _apply_filter_by_type(self, item: Any, filter_type: str, config: dict[str, Any]) -> bool:
        """Apply filter by type for combined filtering."""
        if filter_type == "field":
            temp_filter = FilterNode(filter_type="field", filter_config=config)
            await temp_filter.initialize()
            result = await temp_filter._apply_field_filter(item)
            await temp_filter.cleanup()
            return result is not None
        elif filter_type == "condition":
            temp_filter = FilterNode(filter_type="condition", filter_config=config)
            await temp_filter.initialize()
            result = await temp_filter._apply_condition_filter(item)
            await temp_filter.cleanup()
            return result is not None
        else:
            return True
    
    def add_filter(self, filter_type: str, filter_config: dict[str, Any]) -> None:
        """Add a new filter to the multi-filter."""
        self.filters.append({
            "type": filter_type,
            "config": filter_config
        })
        
        # Update combined filter function
        self.filter_function = self._create_combined_filter(self.filters, self.operator)
    
    def remove_filter(self, index: int) -> bool:
        """Remove a filter by index."""
        if 0 <= index < len(self.filters):
            self.filters.pop(index)
            
            # Update combined filter function
            self.filter_function = self._create_combined_filter(self.filters, self.operator)
            return True
        
        return False
    
    def get_filters_info(self) -> dict[str, Any]:
        """Get information about all configured filters."""
        return {
            "filters": self.filters,
            "operator": self.operator,
            "total_filters": len(self.filters)
        }
