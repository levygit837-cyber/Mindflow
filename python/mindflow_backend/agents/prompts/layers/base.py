"""Base prompt layer — Preamble + Personality + Persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mindflow_backend.agents.prompts.assembler import AssemblyContext
from mindflow_backend.agents.prompts.base import (
    MINDFLOW_PREAMBLE,
    PERSISTENCE_DIRECTIVE,
    build_system_prompt,
)


class BasePromptLayer:
    """Camada base do prompt (Preamble + Personality + Persistence)."""

    name = "base"
    priority = 100  # Máxima prioridade

    def __init__(self, personality: str = "") -> None:
        self._personality = personality

    async def render(self, context: AssemblyContext) -> str:
        if self._personality:
            return build_system_prompt(self._personality)
        return f"{MINDFLOW_PREAMBLE}\n\n{PERSISTENCE_DIRECTIVE}"