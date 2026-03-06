"""Base node classes for MindFlow orchestration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class NodeType(StrEnum):
    """Types of nodes in the system."""
    
    ROUTER = "router"
    EXECUTOR = "executor"
    FORMATTER = "formatter"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    AGENT = "agent"
    TOOL = "tool"
    MEMORY = "memory"
    CUSTOM = "custom"


class NodeCategory(StrEnum):
    """Categories for node classification and routing."""
    
    LLM_INVOKE = "LLM_INVOKE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    SUBGRAPH = "SUBGRAPH"
    INTERNAL = "INTERNAL"
    CONTROL_FLOW = "CONTROL_FLOW"
    DATA_PROCESSING = "DATA_PROCESSING"
    UNKNOWN = "UNKNOWN"


class NodeConfig(BaseModel):
    """Configuration for node execution."""
    
    timeout: Optional[float] = Field(default=30.0, gt=0.0)
    retry_attempts: int = Field(default=3, ge=0)
    enable_streaming: bool = False
    required_inputs: Set[str] = Field(default_factory=set)
    outputs: Set[str] = Field(default_factory=set)
    custom_parameters: Dict[str, Any] = Field(default_factory=dict)


class NodeMetrics(BaseModel):
    """Metrics collected during node execution."""
    
    execution_time: float
    tokens_used: int = 0
    memory_usage: Optional[Dict[str, Any]] = None
    error_count: int = 0
    success_count: int = 0
    last_execution_time: Optional[float] = None


class BaseNode(ABC):
    """Abstract base class for all nodes in MindFlow."""
    
    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        category: NodeCategory = NodeCategory.UNKNOWN,
        config: Optional[NodeConfig] = None,
        description: str = ""
    ) -> None:
        self.node_id = node_id
        self.node_type = node_type
        self.category = category
        self.config = config or NodeConfig()
        self.description = description
        self.metrics = NodeMetrics(
            execution_time=0.0,
            tokens_used=0,
            error_count=0,
            success_count=0,
        )
        self._is_initialized = False
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node logic with the given state."""
        ...
    
    @abstractmethod
    def validate_inputs(self, state: Dict[str, Any]) -> List[str]:
        """Validate that required inputs are present in state."""
        ...
    
    async def initialize(self) -> None:
        """Initialize the node (called once before first execution)."""
        if self._is_initialized:
            return
        
        await self._on_initialize()
        self._is_initialized = True
    
    async def _on_initialize(self) -> None:
        """Override this method for custom initialization logic."""
        pass
    
    async def execute_with_metrics(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the node and collect metrics."""
        import time
        
        start_time = time.time()
        
        try:
            # Validate inputs
            validation_errors = self.validate_inputs(state)
            if validation_errors:
                raise ValueError(f"Input validation failed: {', '.join(validation_errors)}")
            
            # Execute the node
            result = await self.execute(state)
            
            # Update success metrics
            self.metrics.success_count += 1
            self.metrics.last_execution_time = start_time
            
            return result
            
        except Exception as e:
            # Update error metrics
            self.metrics.error_count += 1
            self.metrics.last_execution_time = start_time
            
            # Add error to state
            state["error"] = str(e)
            state["error_node"] = self.node_id
            
            return state
            
        finally:
            # Update execution time
            execution_time = time.time() - start_time
            self.metrics.execution_time += execution_time
    
    def get_node_info(self) -> Dict[str, Any]:
        """Get information about the node."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "category": self.category.value,
            "description": self.description,
            "config": self.config.dict(),
            "metrics": self.metrics.dict(),
            "is_initialized": self._is_initialized,
        }
    
    def reset_metrics(self) -> None:
        """Reset node metrics."""
        self.metrics = NodeMetrics(
            execution_time=0.0,
            tokens_used=0,
            error_count=0,
            success_count=0,
        )
    
    def can_stream(self) -> bool:
        """Check if this node supports streaming."""
        return self.config.enable_streaming
    
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys."""
        return self.config.required_inputs
    
    def get_outputs(self) -> Set[str]:
        """Get the set of output keys this node provides."""
        return self.config.outputs
    
    def __str__(self) -> str:
        return f"{self.node_type.value}:{self.node_id}"
    
    def __repr__(self) -> str:
        return f"Node({self.node_id}, type={self.node_type.value}, category={self.category.value})"


class FunctionNode(BaseNode):
    """Simple node that wraps a callable function."""
    
    def __init__(
        self,
        node_id: str,
        function: callable,
        node_type: NodeType = NodeType.CUSTOM,
        category: NodeCategory = NodeCategory.UNKNOWN,
        config: Optional[NodeConfig] = None,
        description: str = ""
    ) -> None:
        super().__init__(node_id, node_type, category, config, description)
        self.function = function
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the wrapped function."""
        if callable(self.function):
            result = self.function(state)
            if asyncio.iscoroutine(result):
                result = await result
            
            if isinstance(result, dict):
                return result
            else:
                # Wrap non-dict results
                return {"result": result}
        
        raise ValueError(f"Node {self.node_id} has invalid function")
    
    def validate_inputs(self, state: Dict[str, Any]) -> List[str]:
        """Basic validation for function nodes."""
        errors = []
        
        for required_input in self.config.required_inputs:
            if required_input not in state:
                errors.append(f"Missing required input: {required_input}")
        
        return errors


# Import for async detection
import asyncio
