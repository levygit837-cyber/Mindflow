"""Enhanced tool system for MindFlow agents.

Provides modular, extensible tool architecture with:
- Abstract interfaces for consistent tool behavior
- Enhanced registry with granular permissions
- Comprehensive validation and error handling
- Auto-discovery and caching capabilities
- Backward compatibility with existing tools
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, Optional, List, Dict

from deepagents.backends.protocol import BackendProtocol
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import AgentType

# Import new enhanced registry
from .base.tool_registry import EnhancedToolRegistry
from .base.tool_schemas import ToolSchema

# Import tool modules for auto-discovery
from . import filesystem, web, system, code, research

# Legacy imports for backward compatibility (migrated to new locations)
from .web.browser_search import BrowserSearchTool, get_browser_search_tool
from .system.sandbox import MindFlowSandbox, get_sandbox_tool

_logger = get_logger(__name__)

T = TypeVar("T")


class ToolRegistry:
    """Legacy tool registry for backward compatibility.
    
    This class maintains the old interface while delegating
    to the new EnhancedToolRegistry for improved functionality.
    """
    
    def __init__(self, backend: BackendProtocol):
        self.backend = backend
        self._enhanced_registry = EnhancedToolRegistry(backend)
        self._tools: dict[str, tuple[Callable, list[AgentType]]] = {}
        
        # Initialize with default tools for compatibility
        self._initialize_default_tools()
    
    def _initialize_default_tools(self):
        """Initialize default tools for backward compatibility."""
        # Register filesystem tools
        from .filesystem.file_operations import (
            FileReadTool, FileWriteTool, FileEditTool,
            DirectoryListTool, DirectoryCreateTool
        )
        from .filesystem.search_tools import (
            GrepSearchTool, GlobSearchTool, FindFilesTool
        )
        
        # Register web tools
        from .web.http_client import HttpClientTool
        from .web.api_client import ApiClientTool
        
        # Register system tools
        from .system.process_manager import ProcessManagerTool
        
        filesystem_tools = [
            ("read_file", FileReadTool),
            ("write_file", FileWriteTool),
            ("edit_file", FileEditTool),
            ("list_directory", DirectoryListTool),
            ("create_directory", DirectoryCreateTool),
            ("grep_search", GrepSearchTool),
            ("glob_search", GlobSearchTool),
            ("find_files", FindFilesTool),
        ]
        
        web_tools = [
            ("http_client", HttpClientTool),
            ("api_client", ApiClientTool),
        ]
        
        system_tools = [
            ("process_manager", ProcessManagerTool),
        ]
        
        # Register all tools
        all_tools = filesystem_tools + web_tools + system_tools
        
        for tool_name, tool_class in all_tools:
            self._enhanced_registry.register_tool(
                tool_class(),
                name=tool_name
            )
    
    def register_tool(
        self,
        name: str,
        func: Callable,
        scopes: list[AgentType] | None = None,
    ) -> None:
        """Register a tool function with optional agent scopes.
        
        Legacy method - delegates to enhanced registry.
        """
        self._tools[name] = (func, scopes or list(AgentType))
        
        # Also register in enhanced registry if it's a proper tool
        if hasattr(func, '__call__') and hasattr(func, 'get_schema'):
            self._enhanced_registry.register_tool(func, name=name)
        
        _logger.debug("tool_registered", name=name, scopes=str(scopes))
    
    def get_tools_for_agent(self, agent_type: AgentType) -> list[Callable]:
        """Return a list of tool functions authorized for the given agent type."""
        # Get tools from enhanced registry
        tool_names = self._enhanced_registry.get_tools_for_agent(agent_type)
        
        # Convert to legacy format
        authorized_tools = []
        for tool_name in tool_names:
            if tool_name in self._tools:
                authorized_tools.append(self._tools[tool_name][0])
        
        return authorized_tools
    
    def get_all_tool_names(self) -> list[str]:
        """Return a list of all registered tool names."""
        # Combine legacy and enhanced registry tools
        legacy_tools = list(self._tools.keys())
        enhanced_tools = list(self._enhanced_registry._tools.keys())
        return list(set(legacy_tools + enhanced_tools))
    
    @property
    def enhanced_registry(self) -> EnhancedToolRegistry:
        """Access to the enhanced registry for new functionality."""
        return self._enhanced_registry


def create_default_registry(backend: BackendProtocol) -> ToolRegistry:
    """Factory to create a ToolRegistry with standard tools integrated.
    
    Returns legacy ToolRegistry with enhanced capabilities.
    """
    registry = ToolRegistry(backend)
    
    # Register enhanced tools with proper instances
    registry._enhanced_registry.register_tool(
        BrowserSearchTool(),
        name="browser_search"
    )
    
    registry._enhanced_registry.register_tool(
        MindFlowSandbox(),
        name="sandbox"
    )
    
    _logger.info(
        "default_registry_created",
        total_tools=len(registry.get_all_tool_names()),
        enhanced_tools=len(registry._enhanced_registry._tools)
    )
    
    return registry


# Export new enhanced classes for direct use
__all__ = [
    "ToolRegistry",
    "create_default_registry",
    "EnhancedToolRegistry",
    "ToolSchema",
    # Tool modules
    "filesystem",
    "BrowserSearchTool",
    "MindFlowSandbox",
]
