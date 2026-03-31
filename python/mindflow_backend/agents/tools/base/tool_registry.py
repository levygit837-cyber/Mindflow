"""
Tool registry for MindFlow agents. Provides centralized tool management,
registration, discovery, and permission handling.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ToolRegistry:
    """
    Central registry for managing MindFlow tools with permissions and discovery.
    """

    def __init__(self):
        self._tools: dict[str, Any] = {}
        self._permissions: dict[str, dict[str, Any]] = {}
        self._categories: dict[str, list[str]] = {}
        self._initialized = False

    def register_tool(
        self,
        tool_class: type,
        name: str | None = None,
        category: str = "general",
        permissions: dict[str, Any] | None = None
    ) -> bool:
        """
        Register a tool class with the registry.
        Args:
            tool_class: Tool class to register
            name: Optional custom name
            category: Tool category
            permissions: Permission requirements
        Returns:
            True if registration successful
        """
        try:
            tool_name = name or tool_class.__name__
            
            # Check if tool already registered
            if tool_name in self._tools:
                _logger.warning(f"Tool {tool_name} already registered, skipping")
                return False

            # Instantiate tool
            tool_instance = tool_class()
            
            # Store tool
            self._tools[tool_name] = tool_instance
            
            # Store permissions
            self._permissions[tool_name] = permissions or {}
            
            # Add to category
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(tool_name)

            _logger.info(f"Registered tool: {tool_name} in category: {category}")
            return True

        except Exception as e:
            _logger.error(f"Failed to register tool {name}: {str(e)}")
            return False

    def get_tool(self, name: str) -> Any | None:
        """
        Get a tool instance by name.
        Args:
            name: Tool name
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[str]:
        """
        List all registered tools, optionally filtered by category.
        Args:
            category: Optional category filter
        Returns:
            List of tool names
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys())

    def get_categories(self) -> list[str]:
        """
        Get all available categories.
        Returns:
            List of category names
        """
        return list(self._categories.keys())

    def check_permissions(self, tool_name: str, user_permissions: dict[str, Any]) -> bool:
        """
        Check if user has permission to use a tool.
        Args:
            tool_name: Tool name
            user_permissions: User permissions
        Returns:
            True if user has permission
        """
        tool_permissions = self._permissions.get(tool_name, {})
        
        # If no permissions required, allow
        if not tool_permissions:
            return True

        # Check each required permission
        for perm, value in tool_permissions.items():
            if user_permissions.get(perm) != value:
                return False

        return True

    def get_tool_schema(self, name: str) -> dict[str, Any] | None:
        """
        Get schema for a specific tool.
        Args:
            name: Tool name
        Returns:
            Tool schema or None if not found
        """
        tool = self.get_tool(name)
        if tool and hasattr(tool, 'get_schema'):
            return tool.get_schema()
        return None

    def get_all_schemas(self) -> dict[str, dict[str, Any]]:
        """
        Get schemas for all registered tools.
        Returns:
            Dictionary of tool schemas
        """
        schemas = {}
        for name in self._tools:
            schema = self.get_tool_schema(name)
            if schema:
                schemas[name] = schema
        return schemas

    def initialize_from_directory(self, directory_path: str) -> int:
        """
        Auto-discover and register tools from a directory.
        Args:
            directory_path: Path to scan for tools
        Returns:
            Number of tools registered
        """
        if self._initialized:
            _logger.warning("Registry already initialized")
            return 0

        registered_count = 0
        tool_dir = Path(directory_path)

        if not tool_dir.exists():
            _logger.error(f"Tool directory not found: {directory_path}")
            return 0

        # Scan for Python files
        for py_file in tool_dir.glob("**/*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                # Import module dynamically
                module_name = py_file.stem
                spec = __import__(f"mindflow_backend.agents.tools.{module_name}", fromlist=[module_name])
                
                # Look for tool classes
                for attr_name in dir(spec):
                    attr = getattr(spec, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and 
                        any(base.__name__ in ['ToolInterface', 'AsyncToolInterface'] 
                            for base in attr.__bases__)):
                        
                        # Register the tool
                        if self.register_tool(attr):
                            registered_count += 1

            except Exception as e:
                _logger.error(f"Failed to load tools from {py_file}: {str(e)}")

        self._initialized = True
        _logger.info(f"Auto-discovery completed. Registered {registered_count} tools.")
        return registered_count

    def export_registry(self, file_path: str) -> bool:
        """
        Export registry configuration to file.
        Args:
            file_path: Output file path
        Returns:
            True if export successful
        """
        try:
            registry_data = {
                "tools": list(self._tools.keys()),
                "categories": self._categories,
                "permissions": self._permissions,
                "export_timestamp": datetime.now().isoformat()
            }

            with open(file_path, 'w') as f:
                json.dump(registry_data, f, indent=2)

            _logger.info(f"Registry exported to: {file_path}")
            return True

        except Exception as e:
            _logger.error(f"Failed to export registry: {str(e)}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get registry statistics.
        Returns:
            Dictionary with registry stats
        """
        return {
            "total_tools": len(self._tools),
            "total_categories": len(self._categories),
            "tools_by_category": {
                cat: len(tools) for cat, tools in self._categories.items()
            },
            "initialized": self._initialized,
            "last_updated": datetime.now().isoformat()
        }


# Global registry instance
_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    Returns:
        ToolRegistry instance
    """
    return _registry
