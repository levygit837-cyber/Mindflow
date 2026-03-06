"""Enhanced tool registry with granular permissions and auto-discovery.

Provides centralized management of tools with agent-specific permissions,
validation, caching, and dynamic loading capabilities.
"""

from __future__ import annotations

import importlib
import inspect
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from collections.abc import Callable

from deepagents.backends.protocol import BackendProtocol

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.orchestration.orchestrator import AgentType
from .tool_interface import ToolInterface, AsyncToolInterface
from .tool_schemas import (
    ToolSchema, 
    ToolRegistrySchema, 
    ToolExecutionContext,
    ToolValidationError,
    create_tool_schema
)

_logger = get_logger(__name__)


class EnhancedToolRegistry:
    """Enhanced registry for agent tools with granular permissions.
    
    Features:
    - Agent-specific permission control
    - Auto-discovery of tools
    - Schema validation
    - Result caching
    - Dynamic loading
    """
    
    def __init__(self, backend: Optional[BackendProtocol] = None):
        """Initialize the enhanced tool registry.
        
        Args:
            backend: Optional backend for legacy tool integration
        """
        self.backend = backend
        
        # Tool storage
        self._tools: Dict[str, ToolInterface] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._tool_classes: Dict[str, Type[ToolInterface]] = {}
        
        # Permission management
        self._permissions: Dict[str, List[AgentType]] = {}
        self._restrictions: Dict[str, List[AgentType]] = {}
        
        # Performance and caching
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self._config = ToolRegistrySchema(
            name="omnimind_tool_registry",
            auto_discovery=True,
            validation_enabled=True,
            caching_enabled=True
        )
        
        _logger.info("tool_registry_initialized", config=self._config.dict())
    
    def register_tool(
        self,
        tool: Union[ToolInterface, Type[ToolInterface]],
        name: Optional[str] = None,
        allowed_agents: Optional[List[AgentType]] = None,
        restricted_agents: Optional[List[AgentType]] = None,
        schema_override: Optional[ToolSchema] = None
    ) -> bool:
        """Register a tool with the registry.
        
        Args:
            tool: Tool instance or class
            name: Optional custom name (auto-generated if not provided)
            allowed_agents: List of agent types allowed to use this tool
            restricted_agents: List of agent types restricted from using this tool
            schema_override: Custom schema override
            
        Returns:
            True if registration was successful
        """
        try:
            # Handle class vs instance
            if isinstance(tool, type):
                tool_instance = tool()
                tool_class = tool
            else:
                tool_instance = tool
                tool_class = tool.__class__
            
            # Determine name
            tool_name = name or tool_instance.name
            
            # Validate tool interface
            if not isinstance(tool_instance, ToolInterface):
                _logger.error(
                    "tool_registration_failed",
                    tool_name=tool_name,
                    error="Tool does not implement ToolInterface"
                )
                return False
            
            # Get or create schema
            if schema_override:
                schema = schema_override
            else:
                schema = self._extract_schema(tool_instance)
            
            # Validate schema
            if self._config.validation_enabled:
                validation_errors = self._validate_schema(schema)
                if validation_errors:
                    _logger.error(
                        "tool_registration_failed",
                        tool_name=tool_name,
                        errors=validation_errors
                    )
                    return False
            
            # Store tool information
            self._tools[tool_name] = tool_instance
            self._schemas[tool_name] = schema
            self._tool_classes[tool_name] = tool_class
            
            # Set permissions
            self._permissions[tool_name] = allowed_agents or schema.supported_agents
            self._restrictions[tool_name] = restricted_agents or []
            
            # Initialize execution stats
            self._execution_stats[tool_name] = {
                "executions": 0,
                "successes": 0,
                "failures": 0,
                "total_time_ms": 0,
                "last_execution": None
            }
            
            _logger.info(
                "tool_registered",
                name=tool_name,
                category=schema.category,
                allowed_agents=self._permissions[tool_name]
            )
            
            return True
            
        except Exception as e:
            _logger.error(
                "tool_registration_error",
                tool_name=name or "unknown",
                error=str(e)
            )
            return False
    
    def get_tools_for_agent(self, agent_type: AgentType) -> List[str]:
        """Get list of tool names available for specific agent type.
        
        Args:
            agent_type: Agent type to get tools for
            
        Returns:
            List of tool names available to the agent
        """
        available_tools = []
        
        for tool_name, tool in self._tools.items():
            if self.is_tool_available_for_agent(tool_name, agent_type):
                available_tools.append(tool_name)
        
        _logger.debug(
            "tools_retrieved_for_agent",
            agent_type=agent_type.value,
            tool_count=len(available_tools),
            tools=available_tools
        )
        
        return available_tools
    
    def get_tool_instance(self, tool_name: str) -> Optional[ToolInterface]:
        """Get tool instance by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def get_tool_schema(self, tool_name: str) -> Optional[ToolSchema]:
        """Get tool schema by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool schema or None if not found
        """
        return self._schemas.get(tool_name)
    
    def is_tool_available_for_agent(self, tool_name: str, agent_type: AgentType) -> bool:
        """Check if tool is available for specific agent type.
        
        Args:
            tool_name: Name of the tool
            agent_type: Agent type to check
            
        Returns:
            True if tool is available for the agent
        """
        if tool_name not in self._tools:
            return False
        
        # Check restrictions first
        if agent_type in self._restrictions.get(tool_name, []):
            return False
        
        # Check permissions
        allowed_agents = self._permissions.get(tool_name, [])
        return agent_type in allowed_agents
    
    async def execute_tool(
        self,
        tool_name: str,
        agent_type: AgentType,
        parameters: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Execute a tool with validation and tracking.
        
        Args:
            tool_name: Name of the tool to execute
            agent_type: Type of agent executing the tool
            parameters: Tool execution parameters
            context: Optional execution context
            
        Returns:
            Tool execution result
        """
        start_time = time.time()
        
        try:
            # Check tool availability
            if not self.is_tool_available_for_agent(tool_name, agent_type):
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not available for agent {agent_type.value}"
                }
            
            # Get tool instance
            tool = self._tools.get(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"Tool {tool_name} not found"
                }
            
            # Validate parameters
            if self._config.validation_enabled:
                is_valid, error_msg = tool.validate_parameters(parameters)
                if not is_valid:
                    return {
                        "success": False,
                        "error": f"Parameter validation failed: {error_msg}"
                    }
            
            # Check cache if enabled
            if self._config.caching_enabled:
                cache_key = self._generate_cache_key(tool_name, parameters)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    _logger.debug("tool_result_cached", tool_name=tool_name)
                    return cached_result
            
            # Prepare execution context
            if context is None:
                context = ToolExecutionContext(
                    tool_name=tool_name,
                    agent_type=agent_type,
                    parameters=parameters
                )
            
            # Execute tool
            if isinstance(tool, AsyncToolInterface):
                result = await tool.execute_async(**parameters)
            else:
                result = await tool.execute(**parameters)
            
            # Update execution stats
            execution_time_ms = int((time.time() - start_time) * 1000)
            self._update_execution_stats(tool_name, True, execution_time_ms)
            
            # Cache result if successful
            if (self._config.caching_enabled and 
                result.get("success", False) and 
                result.get("cacheable", True)):
                
                cache_key = self._generate_cache_key(tool_name, parameters)
                self._cache_result(cache_key, result)
            
            _logger.info(
                "tool_executed",
                tool_name=tool_name,
                agent_type=agent_type.value,
                success=result.get("success", False),
                execution_time_ms=execution_time_ms
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self._update_execution_stats(tool_name, False, execution_time_ms)
            
            _logger.error(
                "tool_execution_failed",
                tool_name=tool_name,
                agent_type=agent_type.value,
                error=str(e),
                execution_time_ms=execution_time_ms
            )
            
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "tool_name": tool_name,
                "execution_time_ms": execution_time_ms
            }
    
    def discover_tools(self, search_paths: Optional[List[str]] = None) -> int:
        """Auto-discover tools in specified paths.
        
        Args:
            search_paths: List of paths to search for tools
            
        Returns:
            Number of tools discovered and registered
        """
        if not self._config.auto_discovery:
            return 0
        
        discovered_count = 0
        
        # Default search paths
        if search_paths is None:
            base_path = Path(__file__).parent.parent
            search_paths = [
                str(base_path / "filesystem"),
                str(base_path / "web"),
                str(base_path / "code"),
                str(base_path / "system"),
                str(base_path / "research"),
                str(base_path / "analysis"),
                str(base_path / "specialized")
            ]
        
        for search_path in search_paths:
            discovered_count += self._discover_tools_in_path(search_path)
        
        _logger.info(
            "tools_discovered",
            count=discovered_count,
            paths=search_paths
        )
        
        return discovered_count
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive registry information.
        
        Returns:
            Dictionary with registry statistics and configuration
        """
        return {
            "config": self._config.dict(),
            "statistics": {
                "total_tools": len(self._tools),
                "tools_by_category": self._get_tools_by_category(),
                "execution_stats": self._execution_stats,
                "cache_size": len(self._cache)
            },
            "tools": {
                name: {
                    "schema": schema.dict(),
                    "permissions": self._permissions.get(name, []),
                    "restrictions": self._restrictions.get(name, [])
                }
                for name, schema in self._schemas.items()
            }
        }
    
    # Private helper methods
    
    def _extract_schema(self, tool: ToolInterface) -> ToolSchema:
        """Extract schema from tool instance."""
        try:
            schema_dict = tool.get_schema()
            
            # Convert dict to ToolSchema if needed
            if isinstance(schema_dict, dict):
                return ToolSchema(**schema_dict)
            else:
                return schema_dict
                
        except Exception as e:
            _logger.warning(
                "schema_extraction_failed",
                tool_name=tool.name,
                error=str(e)
            )
            
            # Return minimal schema
            return create_tool_schema(
                name=tool.name,
                description=tool.description,
                category="unknown",
                parameters=[]
            )
    
    def _validate_schema(self, schema: ToolSchema) -> List[str]:
        """Validate tool schema."""
        errors = []
        
        if not schema.name:
            errors.append("Tool name is required")
        
        if not schema.description:
            errors.append("Tool description is required")
        
        # Validate parameter names are unique
        param_names = [p.name for p in schema.parameters]
        if len(param_names) != len(set(param_names)):
            errors.append("Parameter names must be unique")
        
        return errors
    
    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for tool execution."""
        import hashlib
        import json
        
        key_data = {
            "tool": tool_name,
            "parameters": sorted(parameters.items())
        }
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        if not self._config.caching_enabled:
            return None
        
        if cache_key not in self._cache:
            return None
        
        timestamp = self._cache_timestamps.get(cache_key, 0)
        age = time.time() - timestamp
        
        if age > self._config.cache_ttl_seconds:
            del self._cache[cache_key]
            del self._cache_timestamps[cache_key]
            return None
        
        return self._cache[cache_key]
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache tool execution result."""
        if not self._config.caching_enabled:
            return
        
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
    
    def _update_execution_stats(self, tool_name: str, success: bool, execution_time_ms: int) -> None:
        """Update execution statistics for a tool."""
        if tool_name not in self._execution_stats:
            return
        
        stats = self._execution_stats[tool_name]
        stats["executions"] += 1
        stats["total_time_ms"] += execution_time_ms
        stats["last_execution"] = time.time()
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
    
    def _discover_tools_in_path(self, path: str) -> int:
        """Discover tools in a specific path."""
        discovered = 0
        
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return 0
            
            # Look for Python files with tool classes
            for py_file in path_obj.glob("*_tool.py"):
                try:
                    module_name = py_file.stem
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for tool classes
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, ToolInterface) and 
                            attr != ToolInterface):
                            
                            if self.register_tool(attr):
                                discovered += 1
                
                except Exception as e:
                    _logger.warning(
                        "tool_discovery_failed",
                        file=str(py_file),
                        error=str(e)
                    )
        
        except Exception as e:
            _logger.error(
                "path_discovery_failed",
                path=path,
                error=str(e)
            )
        
        return discovered
    
    def _get_tools_by_category(self) -> Dict[str, int]:
        """Get count of tools by category."""
        categories = {}
        
        for schema in self._schemas.values():
            category = schema.category
            categories[category] = categories.get(category, 0) + 1
        
        return categories
