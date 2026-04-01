"""Tool injection for agent system prompts.

Generates tool descriptions in XML format compatible with Claude Code,
allowing agents to know which tools are available and how to use them.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger

if TYPE_CHECKING:
    from mindflow_backend.agents._base import BaseAgent
    from mindflow_backend.agents.tools.base.tool_registry import ToolRegistry

_logger = get_logger(__name__)


class ToolPromptInjector:
    """Generates tool descriptions for injection into agent system prompts."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def generate_tool_descriptions(self, agent: BaseAgent) -> str:
        """Generate XML-formatted tool descriptions for the agent."""
        tools = self._get_tools_for_agent(agent)
        if not tools:
            return ""
        descriptions = [self._format_tool_as_xml(tool) for tool in tools]
        return f"""# Available Tools\n\nYou have access to the following tools:\n\n<functions>\n{chr(10).join(descriptions)}\n</functions>"""

    def generate_usage_instructions(self, agent: BaseAgent) -> str:
        """Generate usage instructions based on agent's tool scopes."""
        items = []
        tool_scopes = getattr(agent, "tools", [])
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ToolScope
            if ToolScope.FILESYSTEM in tool_scopes:
                items.extend([
                    "To read files, use the Read tool instead of cat, head, or tail.",
                    "To write files, use the Write tool instead of echo or heredoc.",
                ])
            if ToolScope.SHELL in tool_scopes:
                items.append("Use Bash for system commands that require shell execution.")
        except ImportError:
            pass
        if not items:
            return ""
        return "# Using Your Tools\n\n" + "\n".join(f"- {item}" for item in items)

    def inject_into_system_prompt(self, base_prompt: str, agent: BaseAgent) -> str:
        """Inject tool descriptions into the system prompt."""
        sections = [base_prompt]
        tool_desc = self.generate_tool_descriptions(agent)
        if tool_desc:
            sections.append(tool_desc)
        usage = self.generate_usage_instructions(agent)
        if usage:
            sections.append(usage)
        return "\n\n".join(sections)

    def _get_tools_for_agent(self, agent: BaseAgent) -> list[Any]:
        """Get tool instances available to the agent."""
        tool_scopes = getattr(agent, "tools", [])
        if not tool_scopes:
            return list(self._registry._tools.values())
        tools = []
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ToolScope
            for scope in tool_scopes:
                scope_tools = self._registry.filter_by_category(scope.value)
                tools.extend(scope_tools)
        except (ImportError, AttributeError):
            tools = list(self._registry._tools.values())
        seen = set()
        unique = []
        for tool in tools:
            name = getattr(tool, "name", None) or tool.__class__.__name__
            if name not in seen:
                seen.add(name)
                unique.append(tool)
        return unique

    def _format_tool_as_xml(self, tool: Any) -> str:
        """Format a single tool as XML."""
        name = getattr(tool, "name", None) or tool.__class__.__name__
        desc = getattr(tool, "description", "No description available.")
        schema = getattr(tool, "input_schema", None)
        schema_json = "{}"
        if schema is not None:
            try:
                if hasattr(schema, "model_json_schema"):
                    schema_json = json.dumps(schema.model_json_schema())
                elif hasattr(schema, "schema"):
                    schema_json = json.dumps(schema.schema())
                elif isinstance(schema, dict):
                    schema_json = json.dumps(schema)
            except Exception:
                pass
        return f"<function>\n<name>{name}</name>\n<description>{desc}</description>\n<parameters>{schema_json}</parameters>\n</function>"


def get_tool_descriptions_section(registry: ToolRegistry, agent: BaseAgent) -> str:
    injector = ToolPromptInjector(registry)
    return injector.generate_tool_descriptions(agent)


def inject_tools_into_prompt(base_prompt: str, registry: ToolRegistry, agent: BaseAgent) -> str:
    injector = ToolPromptInjector(registry)
    return injector.inject_into_system_prompt(base_prompt, agent)


__all__ = ["ToolPromptInjector", "get_tool_descriptions_section", "inject_tools_into_prompt"]