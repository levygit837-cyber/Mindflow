"""Core models for the local plugin platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
import re

from mindflow_backend.schemas.orchestration.communication import MissionGraphType
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)


class PluginScope(StrEnum):
    """Plugin installation or override scope."""

    POLICY = "policy"
    LOCAL = "local"
    PROJECT = "project"
    USER = "user"

    @classmethod
    def precedence(cls) -> tuple["PluginScope", ...]:
        return (cls.POLICY, cls.LOCAL, cls.PROJECT, cls.USER)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Normalized plugin manifest."""

    name: str
    version: str = "0.0.0"
    description: str = ""
    author: str | None = None
    commands: str | list[str] | None = None
    agents: str | list[str] | None = None
    skills: str | list[str] | None = None
    hooks: str | list[str] | dict[str, Any] | None = None
    mcp_servers: str | list[str] | dict[str, Any] | None = None
    settings_path: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PluginDescriptor:
    """Discovered plugin with resolved metadata."""

    plugin_id: str
    root_path: Path
    scope: PluginScope
    manifest: PluginManifest
    data_dir: Path
    diagnostics: tuple[str, ...] = ()


def sanitize_plugin_id(plugin_id: str) -> str:
    """Convert a plugin ID into a filesystem-safe token."""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", plugin_id).strip("-") or "plugin"


def _apply_argument_substitutions(template: str, arguments: list[str]) -> str:
    rendered = template.replace("$ARGUMENTS", " ".join(arguments))
    for index, argument in enumerate(arguments):
        rendered = rendered.replace(f"$ARGUMENTS[{index}]", argument)
        rendered = rendered.replace(f"${index}", argument)
    return rendered


@dataclass(frozen=True, slots=True)
class DeclarativeSkillDefinition:
    """Declarative skill loaded from SKILL.md."""

    plugin_id: str
    skill_name: str
    skill_id: str
    description: str
    body: str
    source_path: Path
    skill_dir: Path
    plugin_root: Path
    plugin_data_dir: Path
    allowed_tools: list[str] = field(default_factory=list)
    disable_model_invocation: bool = False
    context_mode: str | None = None
    agent: str | None = None
    hooks: dict[str, Any] = field(default_factory=dict)
    paths: list[str] = field(default_factory=list)
    shell: str | None = None

    def render(self, arguments: list[str], session_id: str | None = None) -> str:
        """Render the skill body with basic Claude-compatible substitutions."""
        rendered = _apply_argument_substitutions(self.body, arguments)
        replacements = {
            "${CLAUDE_SESSION_ID}": session_id or "",
            "${MINDFLOW_SESSION_ID}": session_id or "",
            "${CLAUDE_SKILL_DIR}": str(self.skill_dir),
            "${MINDFLOW_SKILL_DIR}": str(self.skill_dir),
            "${CLAUDE_PLUGIN_ROOT}": str(self.plugin_root),
            "${MINDFLOW_PLUGIN_ROOT}": str(self.plugin_root),
            "${CLAUDE_PLUGIN_DATA}": str(self.plugin_data_dir),
            "${MINDFLOW_PLUGIN_DATA}": str(self.plugin_data_dir),
        }
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered


@dataclass(frozen=True, slots=True)
class DeclarativeCommandDefinition:
    """Declarative command loaded from markdown or promoted from a skill."""

    plugin_id: str
    command_name: str
    namespaced_name: str
    description: str
    body: str
    source_path: Path
    plugin_root: Path
    plugin_data_dir: Path
    kind: str = "command"
    linked_skill_id: str | None = None

    def render(self, arguments: list[str], session_id: str | None = None) -> str:
        """Render the command body with basic substitutions."""
        rendered = _apply_argument_substitutions(self.body, arguments)
        replacements = {
            "${CLAUDE_SESSION_ID}": session_id or "",
            "${MINDFLOW_SESSION_ID}": session_id or "",
            "${CLAUDE_PLUGIN_ROOT}": str(self.plugin_root),
            "${MINDFLOW_PLUGIN_ROOT}": str(self.plugin_root),
            "${CLAUDE_PLUGIN_DATA}": str(self.plugin_data_dir),
            "${MINDFLOW_PLUGIN_DATA}": str(self.plugin_data_dir),
        }
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered


@dataclass(frozen=True, slots=True)
class DeclarativeAgentDefinition:
    """Declarative agent definition loaded from markdown."""

    plugin_id: str
    agent_name: str
    agent_id: str
    description: str
    prompt: str
    source_path: Path
    agent_role: AgentType = AgentType.ANALYST
    tool_scopes: list[ToolScope] | None = None
    sandbox: SandboxMode | None = None
    thinking_level: ThinkingLevel | None = None
    keep_context: bool | None = None
    summary: str = ""
    use_when: str = ""
    available_mission_graphs: tuple[MissionGraphType, ...] = ()
    default_model: str | None = None
    color: str | None = None
    preload_skills: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SkillActivation:
    """Represents activation of a skill for a session."""

    session_id: str
    skill_id: str


@dataclass(frozen=True, slots=True)
class PluginSessionSnapshot:
    """Effective plugin state for a session."""

    session_id: str
    cwd: str
    plugins: list[PluginDescriptor] = field(default_factory=list)
    skills: dict[str, DeclarativeSkillDefinition] = field(default_factory=dict)
    commands: dict[str, DeclarativeCommandDefinition] = field(default_factory=dict)
    agents: dict[str, DeclarativeAgentDefinition] = field(default_factory=dict)
