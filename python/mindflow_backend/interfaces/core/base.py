"""Base interfaces for all MindFlow components.

This module provides fundamental interfaces that establish the foundation
for consistent component behavior across the entire system.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any
from enum import Enum

from .lifecycle import LifecycleInterface
from .config import ConfigurableInterface
from .logging import LoggableInterface


class ComponentStatus(Enum):
    """Status of a component in its lifecycle."""
    
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


@runtime_checkable
class BaseComponentInterface(Protocol):
    """Base interface for all components in the MindFlow system.
    
    Every component, whether it's an agent, service, tool, or infrastructure
    component, should implement this interface to ensure consistent behavior,
    error handling, and observability.
    """
    
    def __init__(self) -> None:
        """Initialize the component."""
        ...
    
    def get_name(self) -> str:
        """Get the unique name of this component.
        
        Returns:
            The component name used for identification and logging.
        """
        ...
    
    def get_version(self) -> str:
        """Get the version of this component.
        
        Returns:
            Version string following semantic versioning.
        """
        ...
    
    def get_component_type(self) -> str:
        """Get the type/category of this component.
        
        Returns:
            Component type (e.g., 'agent', 'service', 'tool', 'infrastructure').
        """
        ...
    
    def handle_error(self, error: Exception, context: str = "") -> Any:
        """Handle errors consistently across all components.
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            
        Returns:
            Error response or re-raises exception based on severity
        """
        ...
    
    def get_metadata(self) -> dict[str, Any]:
        """Get component metadata for discovery and monitoring.
        
        Returns:
            Dictionary containing component metadata like capabilities,
            dependencies, configuration schema, etc.
        """
        ...


@runtime_checkable
class ServiceInterface(BaseComponentInterface, LifecycleInterface, ConfigurableInterface, LoggableInterface, Protocol):
    """Interface for all service components.
    
    Services are stateful components that provide specific functionality
    to other parts of the system. They combine base component capabilities
    with lifecycle management, configuration, and logging.
    """
    
    async def process_request(self, request: Any) -> Any:
        """Process a service request.
        
        Args:
            request: The request to process
            
        Returns:
            The result of processing the request
        """
        ...
    
    async def get_metrics(self) -> dict[str, Any]:
        """Get service metrics for monitoring.
        
        Returns:
            Dictionary containing performance and health metrics
        """
        ...
    
    def get_capabilities(self) -> list[str]:
        """Get the capabilities provided by this service.
        
        Returns:
            List of capability names this service provides
        """
        ...


@runtime_checkable
class AgentInterface(BaseComponentInterface, ConfigurableInterface, LoggableInterface, Protocol):
    """Interface for all agent components.
    
    Agents are intelligent components that can process tasks, make decisions,
    and interact with users or other agents. They combine base capabilities
    with configuration and logging.
    """
    
    async def process_task(self, task: Any) -> Any:
        """Process an agent task.
        
        Args:
            task: The task to process
            
        Returns:
            The result of task processing
        """
        ...
    
    def get_agent_type(self) -> str:
        """Get the specific type of this agent.
        
        Returns:
            Agent type (e.g., 'coder', 'analyst', 'researcher', 'reviewer')
        """
        ...
    
    def get_capabilities(self) -> list[str]:
        """Get the capabilities of this agent.
        
        Returns:
            List of capabilities this agent can perform
        """
        ...


@runtime_checkable
class ToolInterface(BaseComponentInterface, LoggableInterface, Protocol):
    """Interface for all tool components.
    
    Tools are utility components that provide specific functionality
    to agents, such as file operations, web requests, or system interactions.
    """
    
    async def execute(self, input_data: Any) -> Any:
        """Execute the tool with given input.
        
        Args:
            input_data: The input data for tool execution
            
        Returns:
            The result of tool execution
        """
        ...
    
    def get_schema(self) -> dict[str, Any]:
        """Get the schema for this tool's input/output.
        
        Returns:
            Dictionary containing input/output schema definitions
        """
        ...
    
    def requires_state(self) -> bool:
        """Check if this tool requires state management.
        
        Returns:
            True if the tool maintains state between executions
        """
        ...
    
    def get_permissions_required(self) -> list[str]:
        """Get the permissions required for this tool.
        
        Returns:
            List of permission names required to use this tool
        """
        ...


@runtime_checkable
class InfrastructureInterface(BaseComponentInterface, LifecycleInterface, ConfigurableInterface, LoggableInterface, Protocol):
    """Interface for all infrastructure components.
    
    Infrastructure components provide system-level services like databases,
    message queues, caching, and communication protocols.
    """
    
    async def connect(self) -> None:
        """Establish connection to the infrastructure resource."""
        ...
    
    async def disconnect(self) -> None:
        """Close connection to the infrastructure resource."""
        ...
    
    def is_connected(self) -> bool:
        """Check if connected to the infrastructure resource.
        
        Returns:
            True if connected, False otherwise
        """
        ...
    
    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for monitoring.
        
        Returns:
            Dictionary containing connection details and status
        """
        ...
