"""Command adapters for declarative plugin commands and skills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)
from mindflow_backend.plugins.models import DeclarativeCommandDefinition, DeclarativeSkillDefinition


@dataclass
class PluginPromptCommand:
    """A slash command backed by declarative markdown content."""

    definition: DeclarativeCommandDefinition

    def __post_init__(self) -> None:
        self.metadata = CommandMetadata(
            name=self.definition.namespaced_name,
            description=self.definition.description,
            category=CommandCategory.CUSTOM,
        )

    async def execute(self, context: CommandContext) -> CommandResult:
        rendered = self.definition.render(
            context.args,
            session_id=context.session_id,
        )
        return CommandResult(
            success=True,
            message=rendered,
            data={
                "plugin_id": self.definition.plugin_id,
                "command_kind": self.definition.kind,
                "source_path": str(self.definition.source_path),
                "linked_skill_id": self.definition.linked_skill_id,
            },
        )


@dataclass
class PluginSkillCommand:
    """A slash command that activates a declarative skill for a session."""

    definition: DeclarativeSkillDefinition
    plugin_manager: Any

    def __post_init__(self) -> None:
        self.metadata = CommandMetadata(
            name=self.definition.skill_id,
            description=self.definition.description,
            category=CommandCategory.CUSTOM,
        )

    async def execute(self, context: CommandContext) -> CommandResult:
        await self.plugin_manager.activate_skill(
            session_id=context.session_id,
            skill_id=self.definition.skill_id,
        )
        rendered = self.definition.render(
            context.args,
            session_id=context.session_id,
        )
        return CommandResult(
            success=True,
            message=rendered,
            data={
                "plugin_id": self.definition.plugin_id,
                "skill_id": self.definition.skill_id,
                "allowed_tools": self.definition.allowed_tools,
                "source_path": str(self.definition.source_path),
            },
        )
