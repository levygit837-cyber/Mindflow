"""Local-first plugin manager for MindFlow."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from mindflow_backend.agents._registry import get_registry as get_agent_registry
from mindflow_backend.agents.specialists.runtime_policy import (
    AgentRuntimePolicy,
    get_agent_runtime_policy,
    register_session_runtime_policy,
    unregister_session_runtime_policies,
)
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.plugins.frontmatter import normalize_string_list, parse_markdown_file
from mindflow_backend.plugins.manifest import (
    DEFAULT_AGENTS_DIR,
    DEFAULT_COMMANDS_DIR,
    DEFAULT_SKILLS_DIR,
    load_plugin_manifest,
    resolve_component_paths,
    resolve_hook_configs,
)
from mindflow_backend.plugins.models import (
    DeclarativeAgentDefinition,
    DeclarativeCommandDefinition,
    DeclarativeSkillDefinition,
    PluginDescriptor,
    PluginScope,
    PluginSessionSnapshot,
    SkillActivation,
    sanitize_plugin_id,
)
from mindflow_backend.plugins.state_store import PluginStateStore
from mindflow_backend.schemas.orchestration.communication import MissionGraphType
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    SandboxMode,
    ThinkingLevel,
    ToolScope,
)

logger = get_logger(__name__)

_TOOL_SCOPE_ALIASES = {
    "filesystem": ToolScope.FILESYSTEM,
    "read": ToolScope.FILESYSTEM,
    "write": ToolScope.FILESYSTEM,
    "edit": ToolScope.FILESYSTEM,
    "grep": ToolScope.FILESYSTEM,
    "glob": ToolScope.FILESYSTEM,
    "shell": ToolScope.SHELL,
    "bash": ToolScope.SHELL,
    "web_search": ToolScope.WEB_SEARCH,
    "websearch": ToolScope.WEB_SEARCH,
    "browser_search": ToolScope.BROWSER_SEARCH,
    "browsersearch": ToolScope.BROWSER_SEARCH,
    "code_analysis": ToolScope.CODE_ANALYSIS,
    "contextplus": ToolScope.CONTEXTPLUS,
    "database": ToolScope.DATABASE,
    "memory": ToolScope.MEMORY,
    "planning": ToolScope.PLANNING,
    "delegation": ToolScope.DELEGATION,
}


def _parse_agent_role(value: Any) -> AgentType:
    normalized = str(value or "analyst").strip().lower().replace("_", "-")
    aliases = {
        "analyst": AgentType.ANALYST,
        "coder": AgentType.CODER,
        "researcher": AgentType.RESEARCHER,
        "orchestrator": AgentType.ORCHESTRATOR,
    }
    if normalized in aliases:
        return aliases[normalized]
    return AgentType(str(value).strip().lower())


def _parse_sandbox_mode(value: Any) -> SandboxMode | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower().replace("-", "_")
    aliases = {
        "none": SandboxMode.NONE,
        "read_only": SandboxMode.READ_ONLY,
        "readonly": SandboxMode.READ_ONLY,
        "read": SandboxMode.READ_ONLY,
        "full": SandboxMode.FULL,
    }
    return aliases.get(normalized, SandboxMode(str(value).strip().lower()))


def _parse_thinking_level(value: Any) -> ThinkingLevel | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().upper().replace("-", "_")
    return ThinkingLevel(normalized)


def _parse_tool_scopes(value: Any) -> list[ToolScope] | None:
    entries = normalize_string_list(value)
    if not entries:
        return None

    scopes: list[ToolScope] = []
    seen: set[ToolScope] = set()
    for entry in entries:
        normalized = entry.strip().lower().replace("-", "_")
        scope = _TOOL_SCOPE_ALIASES.get(normalized)
        if scope is None:
            try:
                scope = ToolScope(normalized)
            except ValueError:
                logger.warning("plugin_agent_unknown_tool_scope", tool=entry)
                continue
        if scope not in seen:
            seen.add(scope)
            scopes.append(scope)
    return scopes or None


def _parse_mission_graphs(value: Any) -> tuple[MissionGraphType, ...]:
    graphs: list[MissionGraphType] = []
    for entry in normalize_string_list(value):
        normalized = entry.strip().lower()
        try:
            graphs.append(MissionGraphType(normalized))
        except ValueError:
            logger.warning("plugin_agent_unknown_mission_graph", graph=entry)
    return tuple(graphs)


def _substitute_plugin_vars(
    value: str,
    descriptor: PluginDescriptor,
    *,
    skill_dir: Path | None = None,
    session_id: str | None = None,
) -> str:
    replacements = {
        "${CLAUDE_PLUGIN_ROOT}": str(descriptor.root_path),
        "${MINDFLOW_PLUGIN_ROOT}": str(descriptor.root_path),
        "${CLAUDE_PLUGIN_DATA}": str(descriptor.data_dir),
        "${MINDFLOW_PLUGIN_DATA}": str(descriptor.data_dir),
        "${CLAUDE_SESSION_ID}": session_id or "",
        "${MINDFLOW_SESSION_ID}": session_id or "",
    }
    if skill_dir is not None:
        replacements["${CLAUDE_SKILL_DIR}"] = str(skill_dir)
        replacements["${MINDFLOW_SKILL_DIR}"] = str(skill_dir)
    rendered = value
    for key, replacement in replacements.items():
        rendered = rendered.replace(key, replacement)
    return rendered


class PluginManager:
    """Discover, resolve, and activate local plugins."""

    def __init__(
        self,
        plugin_roots: dict[PluginScope, Path] | None = None,
        state_store: PluginStateStore | None = None,
        data_root: Path | None = None,
        hook_manager: HookManager | None = None,
    ) -> None:
        self._explicit_plugin_roots = plugin_roots or {}
        self._state_store = state_store or PluginStateStore()
        self._data_root = data_root or (Path.home() / ".mindflow" / "plugins" / "data")
        self._hook_manager = hook_manager or HookManager.get_instance()
        self._session_snapshots: dict[str, PluginSessionSnapshot] = {}

    @property
    def hook_manager(self) -> HookManager:
        return self._hook_manager

    def activate_session_sync(self, session_id: str, *, cwd: str | None = None) -> PluginSessionSnapshot:
        """Synchronous wrapper for session activation."""
        return _run_sync(self.activate_session(session_id, cwd=cwd))

    async def activate_session(self, session_id: str, *, cwd: str | None = None) -> PluginSessionSnapshot:
        """Resolve and activate plugins for a session."""
        await self.deactivate_session(session_id)

        effective_plugins = self.resolve_enabled_plugins(cwd=cwd)
        skills: dict[str, DeclarativeSkillDefinition] = {}
        commands: dict[str, DeclarativeCommandDefinition] = {}
        agents: dict[str, DeclarativeAgentDefinition] = {}

        for descriptor in effective_plugins:
            descriptor.data_dir.mkdir(parents=True, exist_ok=True)
            self._register_plugin_hooks(session_id=session_id, descriptor=descriptor)

            for command in self._load_commands_for_plugin(descriptor):
                commands[command.namespaced_name] = command

            plugin_skills = self._load_skills_for_plugin(descriptor)
            for skill in plugin_skills:
                skills[skill.skill_id] = skill
                if not skill.disable_model_invocation:
                    commands[skill.skill_id] = DeclarativeCommandDefinition(
                        plugin_id=skill.plugin_id,
                        command_name=skill.skill_name,
                        namespaced_name=skill.skill_id,
                        description=skill.description,
                        body=skill.body,
                        source_path=skill.source_path,
                        plugin_root=skill.plugin_root,
                        plugin_data_dir=skill.plugin_data_dir,
                        kind="skill",
                        linked_skill_id=skill.skill_id,
                    )

            for agent in self._load_agents_for_plugin(
                descriptor,
                available_skills=plugin_skills,
            ):
                agents[agent.agent_id] = agent

        self._register_session_agents(session_id=session_id, agents=agents)

        snapshot = PluginSessionSnapshot(
            session_id=session_id,
            cwd=str(Path(cwd or ".").resolve()),
            plugins=effective_plugins,
            skills=skills,
            commands=commands,
            agents=agents,
        )
        self._session_snapshots[session_id] = snapshot
        return snapshot

    async def deactivate_session(self, session_id: str) -> None:
        """Remove session-scoped hooks and cached plugin state."""
        if session_id not in self._session_snapshots:
            return

        snapshot = self._session_snapshots.pop(session_id)
        for plugin in snapshot.plugins:
            self._hook_manager.unregister_plugin_commands(
                plugin.plugin_id,
                session_id=session_id,
            )
        for skill_id in snapshot.skills:
            self._hook_manager.unregister_skill_commands(
                skill_id,
                session_id=session_id,
            )
        unregister_session_runtime_policies(session_id)
        get_agent_registry().unregister_session_agents(session_id)

    def activate_skill_sync(self, session_id: str, skill_id: str) -> SkillActivation:
        """Synchronous wrapper for skill activation."""
        return _run_sync(self.activate_skill(session_id, skill_id))

    async def activate_skill(self, session_id: str, skill_id: str) -> SkillActivation:
        """Activate skill-scoped hooks for a session."""
        snapshot = self._session_snapshots.get(session_id)
        if snapshot is None:
            raise KeyError(f"Session '{session_id}' has no active plugin snapshot")
        skill = snapshot.skills[skill_id]
        self._hook_manager.register_skill_commands(
            skill_id,
            skill.hooks,
            session_id=session_id,
        )
        return SkillActivation(session_id=session_id, skill_id=skill_id)

    def get_session_snapshot(self, session_id: str) -> PluginSessionSnapshot | None:
        """Return the last activation snapshot for a session."""
        return self._session_snapshots.get(session_id)

    def resolve_enabled_plugins(self, *, cwd: str | None = None) -> list[PluginDescriptor]:
        """Resolve enabled plugins honoring scope precedence."""
        discovered_by_scope = self.discover_plugins(cwd=cwd)
        states = {
            scope: self._state_store.load_state(scope, cwd=cwd)
            for scope in PluginScope.precedence()
        }

        selected: dict[str, PluginDescriptor] = {}
        blocked: set[str] = set()

        for scope in PluginScope.precedence():
            state = states[scope]
            blocked.update(state.disabled_plugins)
            scoped_plugins = {plugin.plugin_id: plugin for plugin in discovered_by_scope.get(scope, [])}
            for plugin_id in state.enabled_plugins:
                if plugin_id in blocked or plugin_id in selected:
                    continue
                descriptor = scoped_plugins.get(plugin_id)
                if descriptor is not None:
                    selected[plugin_id] = descriptor

        return list(selected.values())

    def collect_commands(self, *, cwd: str | None = None) -> list[DeclarativeCommandDefinition]:
        """Collect declarative commands for currently enabled plugins."""
        commands: list[DeclarativeCommandDefinition] = []
        for descriptor in self.resolve_enabled_plugins(cwd=cwd):
            commands.extend(self._load_commands_for_plugin(descriptor))
            for skill in self._load_skills_for_plugin(descriptor):
                if not skill.disable_model_invocation:
                    commands.append(
                        DeclarativeCommandDefinition(
                            plugin_id=skill.plugin_id,
                            command_name=skill.skill_name,
                            namespaced_name=skill.skill_id,
                            description=skill.description,
                            body=skill.body,
                            source_path=skill.source_path,
                            plugin_root=skill.plugin_root,
                            plugin_data_dir=skill.plugin_data_dir,
                            kind="skill",
                            linked_skill_id=skill.skill_id,
                        )
                    )
        return commands

    def discover_plugins(self, *, cwd: str | None = None) -> dict[PluginScope, list[PluginDescriptor]]:
        """Discover all plugin directories by scope."""
        roots = self._resolve_plugin_roots(cwd=cwd)
        discovered: dict[PluginScope, list[PluginDescriptor]] = {}
        for scope, root in roots.items():
            plugins: list[PluginDescriptor] = []
            if not root.exists():
                discovered[scope] = plugins
                continue
            for plugin_dir in sorted(path for path in root.iterdir() if path.is_dir()):
                try:
                    manifest = load_plugin_manifest(plugin_dir)
                    plugin_id = manifest.name
                    descriptor = PluginDescriptor(
                        plugin_id=plugin_id,
                        root_path=plugin_dir,
                        scope=scope,
                        manifest=manifest,
                        data_dir=self._data_root / sanitize_plugin_id(plugin_id),
                    )
                    plugins.append(descriptor)
                except Exception as exc:
                    logger.warning(
                        "plugin_discovery_failed",
                        path=str(plugin_dir),
                        scope=scope.value,
                        error=str(exc),
                    )
            discovered[scope] = plugins
        return discovered

    def _resolve_plugin_roots(self, *, cwd: str | None = None) -> dict[PluginScope, Path]:
        current_dir = Path(cwd or ".").resolve()
        defaults = {
            PluginScope.USER: Path.home() / ".mindflow" / "plugins",
            PluginScope.PROJECT: current_dir / ".mindflow" / "plugins",
            PluginScope.LOCAL: current_dir / ".mindflow" / "local" / "plugins",
            PluginScope.POLICY: Path("/etc/mindflow/plugins"),
        }
        defaults.update(self._explicit_plugin_roots)
        return defaults

    def _register_plugin_hooks(self, *, session_id: str, descriptor: PluginDescriptor) -> None:
        for config in resolve_hook_configs(descriptor.root_path, descriptor.manifest.hooks):
            hooks_config = config.get("hooks", config)
            substituted = self._substitute_hook_commands(
                descriptor=descriptor,
                hooks_config=hooks_config,
                session_id=session_id,
            )
            self._hook_manager.register_plugin_commands(
                descriptor.plugin_id,
                substituted,
                session_id=session_id,
            )

    def _substitute_hook_commands(
        self,
        *,
        descriptor: PluginDescriptor,
        hooks_config: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        substituted: dict[str, Any] = {}
        for event_name, matchers in hooks_config.items():
            normalized_matchers: list[dict[str, Any]] = []
            for matcher in matchers or []:
                hook_entries = []
                for hook in matcher.get("hooks", []):
                    hook_entry = dict(hook)
                    command = hook_entry.get("command")
                    if isinstance(command, str):
                        hook_entry["command"] = _substitute_plugin_vars(
                            command,
                            descriptor,
                            session_id=session_id,
                        )
                    hook_entries.append(hook_entry)
                normalized_matchers.append(
                    {
                        "matcher": matcher.get("matcher"),
                        "hooks": hook_entries,
                    }
                )
            substituted[event_name] = normalized_matchers
        return substituted

    def _load_commands_for_plugin(self, descriptor: PluginDescriptor) -> list[DeclarativeCommandDefinition]:
        command_files: list[Path] = []
        for path in resolve_component_paths(
            descriptor.root_path,
            descriptor.manifest.commands,
            DEFAULT_COMMANDS_DIR,
        ):
            if path.is_dir():
                command_files.extend(sorted(path.glob("*.md")))
            elif path.suffix == ".md":
                command_files.append(path)

        commands: list[DeclarativeCommandDefinition] = []
        for file_path in command_files:
            frontmatter, body = parse_markdown_file(file_path)
            command_name = str(frontmatter.get("name", file_path.stem)).strip()
            description = str(frontmatter.get("description", f"{command_name} command")).strip()
            commands.append(
                DeclarativeCommandDefinition(
                    plugin_id=descriptor.plugin_id,
                    command_name=command_name,
                    namespaced_name=f"{descriptor.plugin_id}:{command_name}",
                    description=description,
                    body=body,
                    source_path=file_path,
                    plugin_root=descriptor.root_path,
                    plugin_data_dir=descriptor.data_dir,
                )
            )
        return commands

    def _load_skills_for_plugin(self, descriptor: PluginDescriptor) -> list[DeclarativeSkillDefinition]:
        skill_files: list[Path] = []
        for path in resolve_component_paths(
            descriptor.root_path,
            descriptor.manifest.skills,
            DEFAULT_SKILLS_DIR,
        ):
            if path.is_dir():
                skill_files.extend(sorted(path.glob("*/SKILL.md")))
                direct_skill = path / "SKILL.md"
                if direct_skill.exists():
                    skill_files.append(direct_skill)

        skills: list[DeclarativeSkillDefinition] = []
        for file_path in skill_files:
            frontmatter, body = parse_markdown_file(file_path)
            skill_name = str(frontmatter.get("name", file_path.parent.name)).strip()
            skill_id = f"{descriptor.plugin_id}:{skill_name}"
            description = str(frontmatter.get("description", skill_name)).strip()
            hooks = frontmatter.get("hooks", {}) or {}
            skill = DeclarativeSkillDefinition(
                plugin_id=descriptor.plugin_id,
                skill_name=skill_name,
                skill_id=skill_id,
                description=description,
                body=_substitute_plugin_vars(
                    body,
                    descriptor,
                    skill_dir=file_path.parent,
                ),
                source_path=file_path,
                skill_dir=file_path.parent,
                plugin_root=descriptor.root_path,
                plugin_data_dir=descriptor.data_dir,
                allowed_tools=normalize_string_list(frontmatter.get("allowed-tools")),
                disable_model_invocation=bool(frontmatter.get("disable-model-invocation", False)),
                context_mode=frontmatter.get("context"),
                agent=frontmatter.get("agent"),
                hooks=self._substitute_hook_commands(
                    descriptor=descriptor,
                    hooks_config=hooks,
                    session_id="",
                ),
                paths=normalize_string_list(frontmatter.get("paths")),
                shell=frontmatter.get("shell"),
            )
            skills.append(skill)
        return skills

    def _load_agents_for_plugin(
        self,
        descriptor: PluginDescriptor,
        *,
        available_skills: list[DeclarativeSkillDefinition] | None = None,
    ) -> list[DeclarativeAgentDefinition]:
        agent_files: list[Path] = []
        for path in resolve_component_paths(
            descriptor.root_path,
            descriptor.manifest.agents,
            DEFAULT_AGENTS_DIR,
        ):
            if path.is_dir():
                agent_files.extend(sorted(path.glob("*.md")))
            elif path.suffix == ".md":
                agent_files.append(path)

        agents: list[DeclarativeAgentDefinition] = []
        available_skills = available_skills or []
        skills_by_name = {skill.skill_name: skill for skill in available_skills}
        skills_by_id = {skill.skill_id: skill for skill in available_skills}

        for file_path in agent_files:
            frontmatter, body = parse_markdown_file(file_path)
            agent_name = str(frontmatter.get("name", file_path.stem)).strip()
            description = str(frontmatter.get("description", agent_name)).strip()
            preload_skills = normalize_string_list(
                frontmatter.get("skills") or frontmatter.get("preload-skills")
            )
            prompt = _substitute_plugin_vars(body, descriptor)
            attached_skill_bodies: list[str] = []
            for skill_ref in preload_skills:
                skill = skills_by_id.get(skill_ref)
                if skill is None:
                    skill = skills_by_name.get(skill_ref)
                if skill is None:
                    skill = skills_by_id.get(f"{descriptor.plugin_id}:{skill_ref}")
                if skill is not None:
                    attached_skill_bodies.append(
                        f"## Attached Skill: {skill.skill_name}\n\n{skill.body}"
                    )
            if attached_skill_bodies:
                prompt = "\n\n".join([prompt, *attached_skill_bodies])
            agent_role = _parse_agent_role(
                frontmatter.get("agent-role")
                or frontmatter.get("agent_role")
                or frontmatter.get("base-agent")
                or frontmatter.get("base_agent")
                or "analyst"
            )
            agents.append(
                DeclarativeAgentDefinition(
                    plugin_id=descriptor.plugin_id,
                    agent_name=agent_name,
                    agent_id=f"{descriptor.plugin_id}:{agent_name}",
                    description=description,
                    prompt=prompt,
                    source_path=file_path,
                    agent_role=agent_role,
                    tool_scopes=_parse_tool_scopes(frontmatter.get("tools")),
                    sandbox=_parse_sandbox_mode(frontmatter.get("sandbox")),
                    thinking_level=_parse_thinking_level(frontmatter.get("thinking")),
                    keep_context=frontmatter.get("keep-context", frontmatter.get("keep_context")),
                    summary=str(frontmatter.get("summary", "")).strip(),
                    use_when=str(frontmatter.get("use-when", description)).strip(),
                    available_mission_graphs=_parse_mission_graphs(
                        frontmatter.get("mission-graphs")
                        or frontmatter.get("mission_graphs")
                    ),
                    default_model=frontmatter.get("model"),
                    color=frontmatter.get("color"),
                    preload_skills=preload_skills,
                    frontmatter=frontmatter,
                )
            )
        return agents

    def _register_session_agents(
        self,
        *,
        session_id: str,
        agents: dict[str, DeclarativeAgentDefinition],
    ) -> None:
        agent_registry = get_agent_registry()
        for agent_definition in agents.values():
            runtime_policy = self._build_agent_runtime_policy(agent_definition)
            register_session_runtime_policy(session_id, runtime_policy)
            agent_registry.register_session_agent(
                session_id,
                runtime_policy.build_agent(),
            )

    def _build_agent_runtime_policy(
        self,
        agent_definition: DeclarativeAgentDefinition,
    ) -> AgentRuntimePolicy:
        base_policy = get_agent_runtime_policy(agent_role=agent_definition.agent_role)
        return AgentRuntimePolicy(
            agent_role=agent_definition.agent_role,
            specialist=None,
            custom_agent_id=agent_definition.agent_id,
            system_prompt=agent_definition.prompt,
            tools=tuple(agent_definition.tool_scopes or base_policy.tools),
            sandbox=agent_definition.sandbox or base_policy.sandbox,
            thinking_level=agent_definition.thinking_level or base_policy.thinking_level,
            keep_context=(
                base_policy.keep_context
                if agent_definition.keep_context is None
                else bool(agent_definition.keep_context)
            ),
            max_iterations=base_policy.max_iterations,
            summary=agent_definition.summary or f"Plugin agent {agent_definition.agent_name}",
            use_when=agent_definition.use_when or agent_definition.description,
            comm_role=base_policy.comm_role,
            available_mission_graphs=(
                agent_definition.available_mission_graphs or base_policy.available_mission_graphs
            ),
            can_observe=base_policy.can_observe,
            mission_types=base_policy.mission_types,
            supports_sub_team=False,
            sub_team_config=None,
        )


_plugin_manager: PluginManager | None = None


def get_plugin_manager() -> PluginManager:
    """Return the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def _run_sync(awaitable: Any) -> Any:
    """Run an awaitable from sync code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("Synchronous plugin helpers cannot be used inside a running event loop") from None
