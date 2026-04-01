"""Tool description layer — wraps existing ToolPromptInjector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mindflow_backend.agents.prompts.assembler import AssemblyContext

if TYPE_CHECKING:
    from mindflow_backend.agents.tools.tool_injection import ToolPromptInjector


class ToolDescriptionLayer:
    """Camada de descrição de ferramentas (XML format)."""

    name = "tools"
    priority = 90  # Alta prioridade

    def __init__(self, injector: "ToolPromptInjector | None" = None) -> None:
        self._injector = injector

    async def render(self, context: AssemblyContext) -> str | None:
        if context.agent is None or self._injector is None:
            return None

        descriptions = self._injector.generate_tool_descriptions(context.agent)
        usage = self._injector.generate_usage_instructions(context.agent)

        parts = []
        if descriptions:
            parts.append(descriptions)
        if usage:
            parts.append(usage)

        return "\n\n".join(parts) if parts else None