"""Enhanced tool system for MindFlow agents.

Provides modular, extensible tool architecture with:
- Abstract interfaces for consistent tool behavior
- Enhanced registry with granular permissions
- Comprehensive validation and error handling
- Auto-discovery and caching capabilities
- Backward compatibility with existing tools
- ToolScope to concrete tool mapping
"""

from __future__ import annotations

from typing import Any
from pathlib import Path

# Core components
from .base.tool_registry import ToolRegistry
from .base.tool_schemas import ToolSchema
from .sandbox import MindFlowSandbox
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class _DefaultRegistry:
    """Enhanced registry that maps ToolScope to concrete tool implementations."""

    def __init__(self, sandbox: MindFlowSandbox, session_id: str | None = None) -> None:
        self.sandbox = sandbox
        self.session_id = session_id
        self._tool_mapping = self._build_tool_mapping()
        self._initialized_tools = {}  # Cache for tool instances

    def _build_tool_mapping(self) -> dict[Any, list[Any]]:
        """Build mapping from AgentType to ToolScope based on agent configurations."""
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ToolScope
            
            return {
                AgentType.CODER: [ToolScope.FILESYSTEM, ToolScope.SHELL],
                AgentType.ANALYST: [ToolScope.CODE_ANALYSIS, ToolScope.FILESYSTEM, ToolScope.SHELL],
                AgentType.RESEARCHER: [ToolScope.WEB_SEARCH, ToolScope.BROWSER_SEARCH],
                AgentType.ORCHESTRATOR: [],  # Orchestrator delegates, doesn't use tools directly
            }
        except ImportError as e:
            _logger.warning(f"Could not import AgentType/ToolScope: {e}")
            return {}

    def _get_tools_for_scope(self, scope: Any) -> list[Any]:
        """Get concrete tool instances for a given ToolScope."""
        cache_key = str(scope)
        if cache_key in self._initialized_tools:
            return self._initialized_tools[cache_key]

        tools = []

        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ToolScope

            if scope == ToolScope.FILESYSTEM:
                tools = self._get_filesystem_tools()
            elif scope == ToolScope.SHELL:
                tools = self._get_shell_tools()
            elif scope == ToolScope.WEB_SEARCH:
                tools = self._get_web_search_tools()
            elif scope == ToolScope.BROWSER_SEARCH:
                tools = self._get_browser_search_tools()
            elif scope == ToolScope.CODE_ANALYSIS:
                tools = self._get_code_analysis_tools()
            elif scope == ToolScope.DATABASE:
                tools = self._get_database_tools()

            # Propagate root_dir from sandbox to all tool instances (root_dir feature).
            # Tools that are aware of root_dir will use it as their base working path.
            root_dir = str(self.sandbox.cwd) if hasattr(self.sandbox, "cwd") else None
            for tool in tools:
                if root_dir and hasattr(tool, "root_dir"):
                    tool.root_dir = root_dir
                if self.session_id and hasattr(tool, "session_id"):
                    tool.session_id = self.session_id

            # Cache the tools
            self._initialized_tools[cache_key] = tools

        except Exception as e:
            _logger.error(f"Error getting tools for scope {scope}: {e}")

        return tools

    def _get_filesystem_tools(self) -> list[Any]:
        """Get filesystem tools."""
        tools = []
        
        try:
            from .filesystem import (
                FileReadTool, FileWriteTool, FileEditTool,
                GrepSearchTool, GlobSearchTool, FindFilesTool,
                DirectoryListTool, FileDeleteTool, DirectoryCreateTool
            )
            
            tools = [
                FileReadTool(),
                FileWriteTool(), 
                FileEditTool(),
                GrepSearchTool(),
                GlobSearchTool(),
                FindFilesTool(),
                DirectoryListTool(),
                FileDeleteTool(),
                DirectoryCreateTool()
            ]
            _logger.info(f"Loaded {len(tools)} filesystem tools")
            
        except ImportError as e:
            _logger.warning(f"Could not import filesystem tools: {e}")
            
        return tools

    def _get_shell_tools(self) -> list[Any]:
        """Get shell/system tools."""
        tools = []
        
        try:
            from .system import (
                ShellExecutorTool,
                ResourceMonitorTool,
                SystemInfoTool,  # Corrigido: SystemInfoCollector → SystemInfoTool
                ProcessManagerTool,
                ShellTabOpenTool,
                ShellTabListTool,
                ShellTabStatusTool,
                ShellTabExecTool,
                ShellTabReadTool,
                ShellTabCloseTool,
            )
            
            tools = [
                ShellExecutorTool(),
                ResourceMonitorTool(),
                SystemInfoTool(),
                ProcessManagerTool(),
                ShellTabOpenTool(),
                ShellTabListTool(),
                ShellTabStatusTool(),
                ShellTabExecTool(),
                ShellTabReadTool(),
                ShellTabCloseTool(),
            ]
            _logger.info(f"Loaded {len(tools)} shell tools")
            
        except ImportError as e:
            _logger.warning(f"Could not import shell tools: {e}")
            
        return tools

    def _get_web_search_tools(self) -> list[Any]:
        """Get web search tools."""
        tools = []
        
        try:
            from .web import (
                WebScraperTool,
                BrowserSearchTool,
                HttpClientTool,
                ApiClientTool
            )
            
            tools = [
                WebScraperTool(),
                BrowserSearchTool(),
                HttpClientTool(),
                ApiClientTool()
            ]
            _logger.info(f"Loaded {len(tools)} web search tools")
            
        except ImportError as e:
            # Try to load tools individually to avoid cascading failures
            try:
                from .web import WebScraperTool
                tools.append(WebScraperTool())
                _logger.info("Loaded WebScraperTool")
            except ImportError as e2:
                _logger.warning(f"Could not import WebScraperTool: {e2}")
                
            try:
                from .web import HttpClientTool
                tools.append(HttpClientTool())
                _logger.info("Loaded HttpClientTool")
            except ImportError as e2:
                _logger.warning(f"Could not import HttpClientTool: {e2}")
                
            try:
                from .web import ApiClientTool
                tools.append(ApiClientTool())
                _logger.info("Loaded ApiClientTool")
            except ImportError as e2:
                _logger.warning(f"Could not import ApiClientTool: {e2}")
                
            try:
                from .web import BrowserSearchTool
                tools.append(BrowserSearchTool())
                _logger.info("Loaded BrowserSearchTool")
            except ImportError as e2:
                _logger.warning(f"Could not import BrowserSearchTool: {e2}")
                
            if not tools:
                _logger.warning(f"Could not import any web search tools: {e}")
            
        return tools

    def _get_browser_search_tools(self) -> list[Any]:
        """Get browser search tools (subset of web tools)."""
        tools = []
        
        try:
            from .web import (
                BrowserSearchTool,
                WebScraperTool
            )
            
            tools = [
                BrowserSearchTool(),
                WebScraperTool()
            ]
            _logger.info(f"Loaded {len(tools)} browser search tools")
            
        except ImportError as e:
            # Try individual imports
            try:
                from .web import BrowserSearchTool
                tools.append(BrowserSearchTool())
                _logger.info("Loaded BrowserSearchTool")
            except ImportError as e2:
                _logger.warning(f"Could not import BrowserSearchTool: {e2}")
                
            try:
                from .web import WebScraperTool
                tools.append(WebScraperTool())
                _logger.info("Loaded WebScraperTool")
            except ImportError as e2:
                _logger.warning(f"Could not import WebScraperTool: {e2}")
                
            if not tools:
                _logger.warning(f"Could not import any browser search tools: {e}")
            
        return tools

    def _get_code_analysis_tools(self) -> list[Any]:
        """Get code analysis tools."""
        tools = []
        
        try:
            # Code tools directory is mostly empty, use filesystem tools as fallback
            from .filesystem import (
                GrepSearchTool,  # Can be used for code search
                FileReadTool,    # Can read code files
                GlobSearchTool   # Can find code files
            )
            
            tools = [
                GrepSearchTool(),
                FileReadTool(),
                GlobSearchTool()
            ]
            _logger.info(f"Loaded {len(tools)} code analysis tools (filesystem-based)")
            
        except ImportError as e:
            _logger.warning(f"Could not import code analysis tools: {e}")
            
        return tools

    def _get_database_tools(self) -> list[Any]:
        """Get database tools."""
        tools = []
        
        try:
            from .data import (
                DatabaseTool,
                CSVProcessorTool
            )
            
            tools = [
                DatabaseTool(),
                CSVProcessorTool()
            ]
            _logger.info(f"Loaded {len(tools)} database tools")
            
        except ImportError as e:
            _logger.warning(f"Could not import database tools: {e}")
            
        return tools

    def get_tools_for_agent(self, agent_type: Any) -> list[Any]:
        """Get tools for a specific agent type."""
        try:
            # Get ToolScope list for this agent type
            scopes = self._tool_mapping.get(agent_type, [])
            
            # Convert ToolScope to concrete tool instances
            tools = []
            for scope in scopes:
                scope_tools = self._get_tools_for_scope(scope)
                tools.extend(scope_tools)
                
            _logger.info(f"Agent {agent_type} got {len(tools)} tools from scopes: {[str(s) for s in scopes]}")
            return tools
            
        except Exception as e:
            _logger.error(f"Error getting tools for agent {agent_type}: {e}")
            return []


def create_default_registry(
    sandbox: MindFlowSandbox,
    session_id: str | None = None,
) -> _DefaultRegistry:
    """Create a default tool registry for an agent sandbox."""
    return _DefaultRegistry(sandbox, session_id=session_id)


__all__ = [
    # Core components
    "ToolRegistry",
    "ToolSchema", 
    "MindFlowSandbox",
    "create_default_registry",
]
