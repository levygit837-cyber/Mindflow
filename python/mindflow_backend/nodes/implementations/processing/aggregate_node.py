"""Aggregate Node - Aggregates data in processing pipelines.

This node performs aggregation operations on collections of data
including sum, count, average, min, max, and custom aggregations.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from mindflow_backend.nodes.base.node import BaseNode, NodeType, NodeCategory
from mindflow_backend.nodes.base.stateful import StatefulNode


class AggregateNode(StatefulNode, BaseNode):
    """Node that aggregates data using various operations.
    
    This node supports various aggregation types:
    - Sum: Sum numeric values
    - Count: Count items matching criteria
    - Average: Calculate average of numeric values
    - Min/Max: Find minimum/maximum values
    - Group: Group items by specified fields
    - Custom: Apply custom aggregation function
    """
    
    def __init__(
        self,
        node_id: str = "aggregate",
        aggregation_type: str = "sum",  # sum, count, avg, min, max, group, custom
        aggregation_function: Optional[Callable[[List[Any]], Any]] = None,
        group_by: Optional[Union[str, List[str]]] = None,
        field_path: Optional[str] = None,
        filter_condition: Optional[Callable[[Any], bool]] = None,
        initial_value: Optional[Any] = None,
        description: str = ""
    ) -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PROCESSING,
            category=NodeCategory.PROCESSING,
            description=description or f"{aggregation_type} aggregation"
        )
        
        self.aggregation_type = aggregation_type.lower()
        self.aggregation_function = aggregation_function
        self.group_by = group_by
        self.field_path = field_path
        self.filter_condition = filter_condition
        self.initial_value = initial_value
        
        # Required inputs
        self.config.required_inputs = {"data"}
        self.config.outputs = {"result", "aggregated_data", "metadata"}
        
        # Internal state
        self._aggregation_count = 0
        self._aggregation_cache = {}
    
    async def initialize(self) -> None:
        """Initialize the aggregate node."""
        await super().initialize()
        
        # Pre-compile aggregation functions for performance
        if self.aggregation_type in ["sum", "count", "avg", "min", "max"]:
            self._compile_aggregation_function()
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the aggregation based on configured type."""
        data = state.get("data", {})
        
        try:
            # Extract field if specified
            if self.field_path:
                data = self._extract_field_data(data, self.field_path)
            
            # Convert to list for aggregation
            data_list = self._convert_to_list(data)
            
            # Apply filter if specified
            if self.filter_condition:
                data_list = [item for item in data_list if self.filter_condition(item)]
            
            # Apply aggregation based on type
            if self.aggregation_type == "sum":
                result = await self._apply_sum_aggregation(data_list)
            elif self.aggregation_type == "count":
                result = await self._apply_count_aggregation(data_list)
            elif self.aggregation_type == "avg":
                result = await self._apply_average_aggregation(data_list)
            elif self.aggregation_type == "min":
                result = await self._apply_min_aggregation(data_list)
            elif self.aggregation_type == "max":
                result = await self._apply_max_aggregation(data_list)
            elif self.aggregation_type == "group":
                result = await self._apply_group_aggregation(data_list)
            elif self.aggregation_type == "custom":
                result = await self._apply_custom_aggregation(data_list)
            else:
                raise ValueError(f"Unsupported aggregation type: {self.aggregation_type}")
            
            self._aggregation_count += 1
            
            return {
                "result": result,
                "aggregated_data": result,
                "metadata": {
                    "aggregation_type": self.aggregation_type,
                    "aggregation_count": self._aggregation_count,
                    "input_count": len(data_list),
                    "field_path": self.field_path,
                    "grouped_by": self.group_by
                }
            }
            
        except Exception as e:
            from mindflow_backend.infra.logging import get_logger
            logger = get_logger(__name__)
            logger.error("aggregate_node_execution_failed", 
                       aggregation_type=self.aggregation_type, 
                       error=str(e))
            
            return {
                "result": self.initial_value,
                "aggregated_data": self.initial_value,
                "error": str(e),
                "metadata": {"aggregation_type": self.aggregation_type, "status": "error"}
            }
    
    async def _apply_sum_aggregation(self, data_list: List[Any]) -> Any:
        """Apply sum aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        # Extract numeric values
        numeric_values = []
        for item in data_list:
            value = self._extract_numeric_value(item)
            if value is not None:
                numeric_values.append(value)
        
        return sum(numeric_values) if numeric_values else 0
    
    async def _apply_count_aggregation(self, data_list: List[Any]) -> Any:
        """Apply count aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        return len(data_list)
    
    async def _apply_average_aggregation(self, data_list: List[Any]) -> Any:
        """Apply average aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        # Extract numeric values
        numeric_values = []
        for item in data_list:
            value = self._extract_numeric_value(item)
            if value is not None:
                numeric_values.append(value)
        
        return sum(numeric_values) / len(numeric_values) if numeric_values else 0
    
    async def _apply_min_aggregation(self, data_list: List[Any]) -> Any:
        """Apply min aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        # Extract numeric values
        numeric_values = []
        for item in data_list:
            value = self._extract_numeric_value(item)
            if value is not None:
                numeric_values.append(value)
        
        return min(numeric_values) if numeric_values else None
    
    async def _apply_max_aggregation(self, data_list: List[Any]) -> Any:
        """Apply max aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        # Extract numeric values
        numeric_values = []
        for item in data_list:
            value = self._extract_numeric_value(item)
            if value is not None:
                numeric_values.append(value)
        
        return max(numeric_values) if numeric_values else None
    
    async def _apply_group_aggregation(self, data_list: List[Any]) -> Any:
        """Apply group aggregation to data list."""
        if self.aggregation_function:
            return await self.aggregation_function(data_list)
        
        if not self.group_by:
            return data_list
        
        # Group data by specified fields
        groups = {}
        
        for item in data_list:
            # Create group key
            if isinstance(self.group_by, str):
                group_key = self._get_group_key(item, [self.group_by])
            else:
                group_key = self._get_group_key(item, self.group_by)
            
            # Add to group
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        return groups
    
    async def _apply_custom_aggregation(self, data_list: List[Any]) -> Any:
        """Apply custom aggregation function to data list."""
        if not self.aggregation_function:
            raise ValueError("Custom aggregation function is required")
        
        return await self.aggregation_function(data_list)
    
    def _extract_numeric_value(self, item: Any) -> Optional[float]:
        """Extract numeric value from an item."""
        if isinstance(item, (int, float)):
            return float(item)
        elif isinstance(item, dict):
            # Try to find numeric field
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    return float(value)
        elif isinstance(item, str):
            # Try to parse as number
            try:
                return float(item)
            except ValueError:
                pass
        
        return None
    
    def _get_group_key(self, item: Any, fields: List[str]) -> str:
        """Create group key from item fields."""
        if isinstance(item, dict):
            key_parts = []
            for field in fields:
                if field in item:
                    key_parts.append(str(item[field]))
            
            return "|".join(key_parts)
        
        return str(item)
    
    def _convert_to_list(self, data: Any) -> List[Any]:
        """Convert data to list format for aggregation."""
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return list(data.values())
        elif data is not None:
            return [data]
        else:
            return []
    
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
    
    def _compile_aggregation_function(self) -> None:
        """Pre-compile aggregation function for performance."""
        # This would implement more sophisticated optimization
        pass
    
    def set_aggregation_type(self, aggregation_type: str) -> None:
        """Change the aggregation type dynamically."""
        if aggregation_type.lower() in ["sum", "count", "avg", "min", "max", "group", "custom"]:
            self.aggregation_type = aggregation_type.lower()
            self._compile_aggregation_function()
    
    def set_aggregation_function(self, aggregation_function: Callable[[List[Any]], Any]) -> None:
        """Set custom aggregation function."""
        self.aggregation_type = "custom"
        self.aggregation_function = aggregation_function
    
    def set_group_by(self, group_by: Union[str, List[str]]) -> None:
        """Set grouping fields."""
        self.group_by = group_by
    
    def set_filter_condition(self, filter_condition: Callable[[Any], bool]) -> None:
        """Set filter condition for aggregation."""
        self.filter_condition = filter_condition
    
    def get_aggregation_info(self) -> Dict[str, Any]:
        """Get information about current aggregation configuration."""
        return {
            "aggregation_type": self.aggregation_type,
            "aggregation_count": self._aggregation_count,
            "has_custom_function": self.aggregation_function is not None,
            "group_by": self.group_by,
            "field_path": self.field_path,
            "has_filter": self.filter_condition is not None,
            "cache_size": len(self._aggregation_cache)
        }
    
    async def cleanup(self) -> None:
        """Cleanup aggregate node resources."""
        self._aggregation_count = 0
        self._aggregation_cache.clear()
        
        await super().cleanup()


class StatisticalAggregateNode(AggregateNode):
    """Specialized node for statistical aggregations."""
    
    def __init__(
        self,
        node_id: str = "statistical_aggregate",
        statistics: List[str] = None,  # mean, median, mode, std_dev, variance
        description: str = "Statistical aggregation operations"
    ) -> None:
        super().__init__(
            node_id=node_id,
            aggregation_type="custom",
            description=description
        )
        
        self.statistics = statistics or ["mean", "median", "mode"]
        
        # Create statistical aggregation function
        self.aggregation_function = self._create_statistical_function(self.statistics)
    
    def _create_statistical_function(self, statistics: List[str]) -> Callable[[List[Any]], Dict[str, Any]]:
        """Create a function that calculates multiple statistics."""
        import statistics as stats_module
        
        async def statistical_function(data_list):
            if not data_list:
                return {}
            
            # Extract numeric values
            numeric_values = []
            for item in data_list:
                value = self._extract_numeric_value(item)
                if value is not None:
                    numeric_values.append(value)
            
            if not numeric_values:
                return {}
            
            result = {}
            
            if "mean" in self.statistics:
                result["mean"] = stats_module.mean(numeric_values)
            
            if "median" in self.statistics:
                result["median"] = stats_module.median(numeric_values)
            
            if "mode" in self.statistics:
                try:
                    result["mode"] = stats_module.mode(numeric_values)
                except stats_module.StatisticsError:
                    result["mode"] = None
            
            if "std_dev" in self.statistics:
                result["std_dev"] = stats_module.stdev(numeric_values) if len(numeric_values) > 1 else 0
            
            if "variance" in self.statistics:
                result["variance"] = stats_module.variance(numeric_values) if len(numeric_values) > 1 else 0
            
            # Additional statistics
            result["count"] = len(numeric_values)
            result["min"] = min(numeric_values)
            result["max"] = max(numeric_values)
            result["sum"] = sum(numeric_values)
            
            return result
        
        return statistical_function


class GroupByAggregateNode(AggregateNode):
    """Specialized node for group-by aggregations."""
    
    def __init__(
        self,
        node_id: str = "group_by_aggregate",
        group_fields: List[str],
        aggregations: Dict[str, str],  # field_name -> aggregation_type
        description: str = "Group-by aggregation operations"
    ) -> None:
        super().__init__(
            node_id=node_id,
            aggregation_type="group",
            group_by=group_fields,
            description=description
        )
        
        self.group_fields = group_fields
        self.aggregations = aggregations
        
        # Override aggregation function
        self.aggregation_function = self._create_group_by_function(self.aggregations)
    
    def _create_group_by_function(self, aggregations: Dict[str, str]) -> Callable[[List[Any]], Dict[str, Any]]:
        """Create a function that performs group-by aggregations."""
        async def group_by_function(data_list):
            if not data_list:
                return {}
            
            # Group data
            groups = {}
            for item in data_list:
                if not isinstance(item, dict):
                    continue
                
                # Create group key
                group_key = self._get_group_key(item, self.group_fields)
                
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(item)
            
            # Apply aggregations to each group
            result = {}
            for group_key, group_items in groups.items():
                result[group_key] = {}
                
                for field_name, agg_type in aggregations.items():
                    # Extract field values from group items
                    field_values = []
                    for item in group_items:
                        if field_name in item:
                            field_values.append(item[field_name])
                    
                    # Apply aggregation
                    temp_aggregator = AggregateNode(
                        node_id=f"temp_{agg_type}",
                        aggregation_type=agg_type
                    )
                    await temp_aggregator.initialize()
                    agg_result = await temp_aggregator._apply_aggregation_by_type(field_values, agg_type)
                    await temp_aggregator.cleanup()
                    
                    result[group_key][field_name] = agg_result
            
            return result
        
        return group_by_function
    
    async def _apply_aggregation_by_type(self, values: List[Any], agg_type: str) -> Any:
        """Apply aggregation by type to values."""
        temp_aggregator = AggregateNode(
            node_id=f"temp_{agg_type}",
            aggregation_type=agg_type
        )
        await temp_aggregator.initialize()
        result = await temp_aggregator._apply_aggregation_by_type(values, agg_type)
        await temp_aggregator.cleanup()
        return result
