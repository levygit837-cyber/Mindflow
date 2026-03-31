"""Tool registry for MindFlow.

Mirrors Claude Code CLI tool pool assembly (tools.ts):
- getAllBaseTools() → list of all available tools
- getTools(permissionContext) → filtered tool list
- filterToolsByDenyRules() → remove denied tools
- Tool registry with metadata

Design principles:
- Tools register themselves with their schema
- Registry provides filtered lists based on context
- Deny rules filter tools before they're offered to the model
"""

from __future__ import annotations

import fnmatch
from typing import Any, Callable

from pydantic import BaseModel

from mindflow_backend.schemas.tools.base import ToolSchema
from mindflow_backend.schemas.tools.permission import PermissionRule


# ---------------------------------------------------------------------------
# Tool Metadata
# ---------------------------------------------------------------------------


class ToolRegistration(BaseModel):
    """Metadata for a registered tool."""

    model_config = {"extra": "ignore", "populate_by_name": True}

    name: str
    description: str
    schema: ToolSchema | None = None
    category: str = "general"
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_destructive: bool = False
    is_enabled: bool = True
    should_defer: bool = False
    always_load: bool = False


# ---------------------------------------------------------------------------
# Registry Functions
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Central registry for all MindFlow tools.

    Singleton pattern — use get_registry() to access the instance.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistration] = {}
        self._deny_rules: list[PermissionRule] = []

    @property
    def tools(self) -> list[ToolRegistration]:
        return list(self._tools.values())

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    # -- Registration --

    def register(self, registration: ToolRegistration) -> None:
        """Register a tool with the registry."""
        self._tools[registration.name] = registration

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)

    # -- Deny Rules --

    def add_deny_rule(self, rule: PermissionRule) -> None:
        """Add a deny rule for tool filtering."""
        self._deny_rules.append(rule)

    def clear_deny_rules(self) -> None:
        """Remove all deny rules."""
        self._deny_rules.clear()

    @property
    def deny_rules(self) -> list[PermissionRule]:
        return list(self._deny_rules)

    # -- Filtering --

    def filter_by_pattern(self, pattern: str) -> list[ToolRegistration]:
        """Get tools matching a glob pattern."""
        return [
            tool
            for tool in self._tools.values()
            if fnmatch.fnmatch(tool.name.lower(), pattern.lower())
        ]

    def filter_by_category(self, category: str) -> list[ToolRegistration]:
        """Get tools in a specific category."""
        return [
            tool
            for tool in self._tools.values()
            if tool.category.lower() == category.lower()
        ]

    def filter_by_deny_rules(
        self,
        tools: list[ToolRegistration] | None = None,
    ) -> list[ToolRegistration]:
        """Filter tools by current deny rules.

        Similar to Claude Code's filterToolsByDenyRules() — removes tools
        that match any blanket deny rule (pattern with no constraint).
        """
        candidates = tools or self.tools

        def is_denied(tool: ToolRegistration) -> bool:
            for rule in self._deny_rules:
                # Check if rule matches tool name
                if fnmatch.fnmatch(tool.name, rule.tool_pattern):
                    # Blanket deny (no constraints) = filtered out
                    if not rule.has_constraint:
                        return True
            return False

        return [tool for tool in candidates if not is_denied(tool)]

    def get_enabled_tools(
        self,
        tools: list[ToolRegistration] | None = None,
    ) -> list[ToolRegistration]:
        """Get only enabled tools, filtered by deny rules."""
        candidates = tools or self.tools
        enabled = [tool for tool in candidates if tool.is_enabled]
        return self.filter_by_deny_rules(enabled)


# ---------------------------------------------------------------------------
# Lazy Registration Pattern (Claude Code style)
# ---------------------------------------------------------------------------


class LazyToolRegistration:
    """Tool registration that loads tools lazily on first access.

    Similar to how Claude Code uses feature flags and lazy requires
    to avoid loading expensive tools until needed.
    """

    def __init__(self, factory: Callable[[], ToolRegistration]) -> None:
        self._factory = factory
        self._registration: ToolRegistration | None = None

    def resolve(self) -> ToolRegistration:
        if self._registration is None:
            self._registration = self._factory()
        return self._registration


# ---------------------------------------------------------------------------
# Singleton Access
# ---------------------------------------------------------------------------


_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global tool registry (for testing)."""
    global _registry
    _registry = None