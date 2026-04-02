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

from pathlib import Path
from typing import Any

from mindflow_backend.agents.specialists.runtime_policy import AGENT_RUNTIME_POLICY
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

from mindflow_backend.agents.tools.contextplus_fallback import (
    ContextPlusFallbackEngine,
    FallbackConfig,
    FALLBACK_CHAINS,
)
from mindflow_backend.agents.tools.contextplus_validator import (
    ContextPlusValidator,
    ValidationConfig,
)

# Core components
from .base.tool_registry import ToolRegistry
from .base.tool_schemas import ToolSchema
from .sandbox import MindFlowSandbox
from .workspace_security import normalize_sandbox_mode, secure_sandbox_enabled

_logger = get_logger(__name__)


class _DefaultRegistry:
    """Enhanced registry that maps ToolScope to concrete tool implementations."""

    def __init__(
        self,
        sandbox: MindFlowSandbox,
        session_id: str | None = None,
        execution_id: str | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.session_id = session_id
        self.execution_id = execution_id
        self._tool_mapping = self._build_tool_mapping()
        self._initialized_tools = {}  # Cache for tool instances

    def _build_tool_mapping(self) -> dict[Any, list[Any]]:
        """Build mapping from AgentType to ToolScope based on canonical policy."""
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import AgentType, ToolScope

            mapping: dict[Any, list[Any]] = {}
            for policy in AGENT_RUNTIME_POLICY.values():
                if policy.specialist is None:
                    mapping[policy.agent_role] = list(policy.tools)
            return mapping
        except ImportError as e:
            _logger.warning(f"Could not import AgentType/ToolScope: {e}")
            return {}

    def _get_tools_for_scope(self, scope: Any) -> list[Any]:
        """Get concrete tool instances for a given ToolScope.

        Phase 3: Prefers CallableTools when available, falls back to legacy tools.
        """
        cache_key = str(scope)
        if cache_key in self._initialized_tools:
            return self._initialized_tools[cache_key]

        tools = []

        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ToolScope

            # Phase 3: Try to get CallableTools first
            try:
                from mindflow_backend.agents.tools.callable.scope_mapping import (
                    get_callable_tools_for_scope,
                )
                callable_tools = get_callable_tools_for_scope(scope)
                if callable_tools:
                    _logger.debug(f"Using {len(callable_tools)} CallableTools for scope {scope}")
                    tools = callable_tools
                    self._initialized_tools[cache_key] = tools
                    return tools
            except Exception as e:
                _logger.debug(f"CallableTools not available for scope {scope}: {e}")

            # Fallback to legacy tools if CallableTools not available
            if scope == ToolScope.FILESYSTEM:
                tools = self._get_filesystem_tools()
            elif scope == ToolScope.SHELL:
                tools = self._get_shell_tools()
            elif scope == ToolScope.WEB_SEARCH:
                tools = self._get_web_search_tools()
            elif scope == ToolScope.BROWSER_SEARCH:
                tools = self._get_browser_search_tools()
            elif scope == ToolScope.PINCHTAB_FLEET:
                tools = self._get_pinchtab_fleet_tools()
            elif scope == ToolScope.PINCHTAB_BROWSER:
                tools = self._get_pinchtab_browser_tools()
            elif scope == ToolScope.CODE_ANALYSIS:
                tools = self._get_code_analysis_tools()
            elif scope == ToolScope.DATABASE:
                tools = self._get_database_tools()
            elif scope == ToolScope.MEMORY:
                tools = self._get_memory_tools()
            elif scope == ToolScope.PLANNING:
                tools = self._get_planning_tools()
            elif scope == ToolScope.DELEGATION:
                tools = self._get_delegation_tools()

            # Propagate root_dir from sandbox to all tool instances (root_dir feature).
            # Tools that are aware of root_dir will use it as their base working path.
            root_dir = str(self.sandbox.cwd) if hasattr(self.sandbox, "cwd") else None
            for tool in tools:
                if root_dir and hasattr(tool, "root_dir"):
                    tool.root_dir = root_dir
                if self.session_id and hasattr(tool, "session_id"):
                    tool.session_id = self.session_id
                if self.execution_id and hasattr(tool, "execution_id"):
                    tool.execution_id = self.execution_id

            # Cache the tools
            self._initialized_tools[cache_key] = tools

        except Exception as e:
            _logger.error(f"Error getting tools for scope {scope}: {e}")

        return tools

    def _get_filesystem_tools(self) -> list[Any]:
        """Get filesystem tools (v2 by default, v1 for backward compatibility)."""
        tools = []

        try:
            # Import v2 tools (Claude Code standard)
            from .filesystem import (
                FileReadToolV2,
                FileWriteToolV2,
                FileEditToolV2,
                GrepToolV2,
                GlobToolV2,
            )

            # Import v1 tools for backward compatibility
            from .filesystem import (
                DirectoryCreateTool,
                DirectoryListTool,
                FileDeleteTool,
                FindFilesTool,
            )

            tools = [
                # v2 tools (default)
                FileReadToolV2(),
                FileWriteToolV2(),
                FileEditToolV2(),
                GrepToolV2(),
                GlobToolV2(),

                # v1 tools (backward compatibility)
                FindFilesTool(),
                DirectoryListTool(),
                FileDeleteTool(),
                DirectoryCreateTool()
            ]
            _logger.info(f"Loaded {len(tools)} filesystem tools (5 v2 + 4 v1)")

        except ImportError as e:
            _logger.warning(f"Could not import filesystem tools: {e}")

        return tools

    def _get_shell_tools(self) -> list[Any]:
        """Get shell/system tools (v2 by default, v1 for backward compatibility)."""
        tools = []

        try:
            # Import v2 tools (Claude Code standard)
            from .system import ShellExecutorToolV2

            # Import v1 and other system tools
            from .system import (
                ProcessManagerTool,
                ResourceMonitorTool,
                ShellTabCloseTool,
                ShellTabExecTool,
                ShellTabListTool,
                ShellTabOpenTool,
                ShellTabReadTool,
                ShellTabStatusTool,
                SystemInfoTool,
            )

            tools = [
                # v2 tools (default)
                ShellExecutorToolV2(),

                # Other system tools
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
            _logger.info(f"Loaded {len(tools)} shell tools (1 v2 + 9 other)")

        except ImportError as e:
            _logger.warning(f"Could not import shell tools: {e}")

        return tools

    def _get_web_search_tools(self) -> list[Any]:
        """Get web search tools."""
        tools = []
        
        try:
            from .web import (
                ApiClientTool,
                HttpClientTool,
                WebScraperTool,
            )
            
            tools = [
                WebScraperTool(),
                HttpClientTool(),
                ApiClientTool(),
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
                
            if not tools:
                _logger.warning(f"Could not import any web search tools: {e}")
            
        return tools

    def _get_browser_search_tools(self) -> list[Any]:
        """Get compatibility tools for the legacy browser_search scope."""
        tools = []
        
        try:
            from .web import (
                BrowserSearchTool,
                PinchTabFleetTool,
            )
            
            tools = [
                BrowserSearchTool(),
                PinchTabFleetTool(),
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
                from .web import PinchTabFleetTool
                tools.append(PinchTabFleetTool())
                _logger.info("Loaded PinchTabFleetTool")
            except ImportError as e2:
                _logger.warning(f"Could not import PinchTabFleetTool: {e2}")
                
            if not tools:
                _logger.warning(f"Could not import any browser search tools: {e}")
            
        return tools

    def _get_pinchtab_fleet_tools(self) -> list[Any]:
        """Get PinchTab fleet management tools."""
        tools = []

        try:
            from .web import PinchTabFleetTool

            tools = [PinchTabFleetTool()]
            _logger.info(f"Loaded {len(tools)} PinchTab fleet tools")
        except ImportError as e:
            _logger.warning(f"Could not import PinchTab fleet tools: {e}")

        return tools

    def _get_pinchtab_browser_tools(self) -> list[Any]:
        """Get PinchTab per-browser control tools."""
        tools = []

        try:
            from .web import PinchTabBrowserTool

            tools = [PinchTabBrowserTool()]
            _logger.info(f"Loaded {len(tools)} PinchTab browser tools")
        except ImportError as e:
            _logger.warning(f"Could not import PinchTab browser tools: {e}")

        return tools

    def _get_code_analysis_tools(self) -> list[Any]:
        """Get code analysis tools (using v2 filesystem tools)."""
        tools = []

        try:
            from .code import (
                GitNexusContextTool,
                GitNexusImpactTool,
                GitNexusQueryTool,
                GitNexusStatusTool,
            )
            from .filesystem import (
                FileReadToolV2,
                GlobToolV2,
                GrepToolV2,
            )

            tools = [
                GitNexusStatusTool(),
                GitNexusQueryTool(),
                GitNexusContextTool(),
                GitNexusImpactTool(),
                FileReadToolV2(),
                GrepToolV2(),
                GlobToolV2()
            ]
            _logger.info(f"Loaded {len(tools)} code analysis tools (GitNexus + v2 filesystem fallback)")

        except ImportError as e:
            _logger.warning(f"Could not import code analysis tools: {e}")

        return tools

    def _get_database_tools(self) -> list[Any]:
        """Get database tools."""
        tools = []
        
        try:
            from .data import CSVProcessorTool, DatabaseTool
            
            tools = [
                DatabaseTool(),
                CSVProcessorTool()
            ]
            _logger.info(f"Loaded {len(tools)} database tools")
            
        except ImportError as e:
            _logger.warning(f"Could not import database tools: {e}")
            
        return tools

    def _get_memory_tools(self) -> list[Any]:
        """Get memory tools (facts, task context, session recall)."""
        tools = []

        try:
            from .integration.memory_tools import (
                RecallSessionMemoryTool,
                RetrieveTaskContextTool,
                SearchFactsTool,
                StoreFactTool,
            )

            tools = [
                StoreFactTool(),
                SearchFactsTool(),
                RetrieveTaskContextTool(),
                RecallSessionMemoryTool(),
            ]
            _logger.info(f"Loaded {len(tools)} memory tools")

        except ImportError as e:
            _logger.warning(f"Could not import memory tools: {e}")

        return tools

    def _get_planning_tools(self) -> list[Any]:
        """Get planning tools for orchestrator todo-list workflows."""
        tools = []

        try:
            from .planning import (
                FocusTodosTool,
                ReadTodosTool,
                WriteTodosTool,
            )

            tools = [
                WriteTodosTool(),
                ReadTodosTool(),
                FocusTodosTool(),
            ]
            _logger.info(f"Loaded {len(tools)} planning tools")

        except ImportError as e:
            _logger.warning(f"Could not import planning tools: {e}")

        return tools

    def _get_delegation_tools(self) -> list[Any]:
        """Get delegation tools for the orchestrator."""
        tools = []

        try:
            from .orchestration import DelegateToAgentTool

            tools = [DelegateToAgentTool()]
            _logger.info(f"Loaded {len(tools)} delegation tools")

        except ImportError as e:
            _logger.warning(f"Could not import delegation tools: {e}")

        return tools

    def _get_contextplus_analysis_tools(self) -> list[Any]:
        """Get Context+ analysis tools for codebase exploration."""
        return [
            ContextPlusFallbackEngine,
            ContextPlusValidator,
        ]

    def get_tools_for_scopes(self, scopes: list[Any]) -> list[Any]:
        """Get concrete tool instances for an explicit scope list."""
        tools = []
        for scope in scopes:
            tools.extend(self._get_tools_for_scope(scope))
        return tools

    def get_all_tool_names(self) -> list[str]:
        """Return the union of all known tool names, including legacy aliases."""
        tool_names: set[str] = set()
        for scopes in self._tool_mapping.values():
            for tool in self.get_tools_for_scopes(scopes):
                tool_names.add(tool.name)
                if tool.name == "list_dir":
                    tool_names.add("ls_info")
        return sorted(tool_names)

    def _apply_tool_policy(self, tools: list[Any], sandbox_mode: Any) -> list[Any]:
        """Filter tools according to the secure sandbox policy."""
        if not secure_sandbox_enabled():
            return tools

        filtered = []
        normalized_mode = normalize_sandbox_mode(sandbox_mode)
        blocked_in_secure_mode = {"process_manager"}
        blocked_in_read_only = {"write_file", "edit_file", "delete_file", "mkdir"}
        safe_without_system_access = {
            "write_todos",
            "read_todos",
            "focus_todos",
            "store_fact",
            "search_facts",
            "retrieve_task_context",
            "recall_session_memory",
            "delegate_to_agent",
        }

        for tool in tools:
            if tool.name in blocked_in_secure_mode:
                continue
            if normalized_mode == SandboxMode.NONE and tool.name not in safe_without_system_access:
                continue
            if normalized_mode == SandboxMode.READ_ONLY and tool.name in blocked_in_read_only:
                continue
            if normalized_mode != SandboxMode.FULL and tool.name.startswith("shell_tab_"):
                continue
            filtered.append(tool)
        return filtered

    def _configure_tool_instances(self, tools: list[Any], agent: Any | None, sandbox_mode: Any) -> list[Any]:
        """Propagate runtime sandbox state to tool instances."""
        root_dir = getattr(agent, "root_dir", None) or str(self.sandbox.cwd)
        secure_mode = secure_sandbox_enabled()
        for tool in tools:
            if hasattr(tool, "root_dir"):
                tool.root_dir = root_dir
            if self.session_id and hasattr(tool, "session_id"):
                tool.session_id = self.session_id
            if self.execution_id and hasattr(tool, "execution_id"):
                tool.execution_id = self.execution_id
            if hasattr(tool, "sandbox_mode"):
                tool.sandbox_mode = sandbox_mode
            if hasattr(tool, "secure_mode"):
                tool.secure_mode = secure_mode
        return tools

    def get_tools_for_agent(self, agent_or_type: Any) -> list[Any]:
        """Get tools for a specific agent configuration or agent type."""
        try:
            agent = agent_or_type if hasattr(agent_or_type, "tools") else None
            if agent is not None:
                sandbox_mode = getattr(agent, "sandbox", getattr(self.sandbox, "mode", None))
                scopes = list(getattr(agent, "tools", []) or [])
                agent_label = getattr(agent, "agent_id", getattr(agent, "agent_role", "unknown"))
            else:
                sandbox_mode = getattr(self.sandbox, "mode", None)
                scopes = self._tool_mapping.get(agent_or_type, [])
                agent_label = agent_or_type

            tools = self.get_tools_for_scopes(scopes)
            tools = self._configure_tool_instances(tools, agent, sandbox_mode)
            tools = self._apply_tool_policy(tools, sandbox_mode)
            _logger.info(f"Agent {agent_label} got {len(tools)} tools from scopes: {[str(s) for s in scopes]}")
            return tools
            
        except Exception as e:
            _logger.error(f"Error getting tools for agent {agent_or_type}: {e}")
            return []


def create_default_registry(
    sandbox: MindFlowSandbox,
    session_id: str | None = None,
    execution_id: str | None = None,
) -> _DefaultRegistry:
    """Create a default tool registry for an agent sandbox."""
    return _DefaultRegistry(sandbox, session_id=session_id, execution_id=execution_id)


__all__ = [
    # Core components
    "ToolRegistry",
    "ToolSchema", 
    "MindFlowSandbox",
    "create_default_registry",
]
