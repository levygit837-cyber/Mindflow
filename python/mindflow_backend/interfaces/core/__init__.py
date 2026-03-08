"""Core fundamental interfaces for MindFlow backend.

Provides foundational interfaces that all system components should implement
to ensure consistency, proper lifecycle management, and standard patterns.
"""

from .base import BaseComponentInterface
from .lifecycle import LifecycleInterface, ComponentStatus
from .config import ConfigurableInterface
from .logging import LoggableInterface, LogLevel

# Common composite interfaces
from .base import (
    ServiceInterface,
    AgentInterface,
    ToolInterface,
    InfrastructureInterface,
)

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
