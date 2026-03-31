"""Core fundamental interfaces for MindFlow backend.

Provides foundational interfaces that all system components should implement
to ensure consistency, proper lifecycle management, and standard patterns.
"""

# Common composite interfaces
from .base import (
    AgentInterface,
    BaseComponentInterface,
    InfrastructureInterface,
    ServiceInterface,
    ToolInterface,
)
from .config import ConfigurableInterface
from .lifecycle import ComponentStatus, LifecycleInterface
from .logging import LoggableInterface, LogLevel

__all__ = [
    # Base interfaces
    "BaseComponentInterface",
    "LifecycleInterface",
    "ConfigurableInterface", 
    "LoggableInterface",
    
    # Enums and types
    "ComponentStatus",
    "LogLevel",
    
    # Composite interfaces
    "ServiceInterface",
    "AgentInterface",
    "ToolInterface", 
    "InfrastructureInterface",
]
