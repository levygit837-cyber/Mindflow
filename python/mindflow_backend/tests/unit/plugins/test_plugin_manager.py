"""Tests for the local plugin platform."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from mindflow_backend.agents._registry import get_agent, get_registry
from mindflow_backend.agents.specialists.runtime_policy import (
    get_agent_runtime_policy,
    unregister_session_runtime_policies,
)
from mindflow_backend.hooks import HookEvent
from mindflow_backend.plugins.manager import PluginManager
from mindflow_backend.plugins.models import PluginScope
from mindflow_backend.plugins.state_store import PluginStateStore
from mindflow_backend.schemas.orchestration.orchestrator import (
    AgentType,
    ExecutionStrategy,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowRouteDecision


def _write_plugin(
    root: Path,
    plugin_id: str,
    *,
    version: str = "1.0.0",
    hooks: dict | None = None,
    skill_frontmatter: str | None = None,
    skill_body: str = "Skill body",
    agent_frontmatter: str | None = None,
    agent_body: str = "Agent body",
) -> Path:
    plugin_dir = root / plugin_id
    manifest_dir = plugin_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps(
            {
                "name": plugin_id,
                "version": version,
                "description": f"{plugin_id} plugin",
            }
        )
    )

    if hooks is not None:
        hooks_dir = plugin_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        (hooks_dir / "hooks.json").write_text(json.dumps({"hooks": hooks}))

    if skill_frontmatter is not None:
        skill_dir = plugin_dir / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\n{skill_frontmatter}\n---\n\n{skill_body}\n"
        )

    if agent_frontmatter is not None:
        agent_dir = plugin_dir / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "custom-agent.md").write_text(
            f"---\n{agent_frontmatter}\n---\n\n{agent_body}\n"
        )

    return plugin_dir


def _write_state(path: Path, enabled_plugins: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"enabled_plugins": enabled_plugins}))


@pytest.fixture
def scoped_manager(tmp_path: Path) -> PluginManager:
    user_root = tmp_path / "user-plugins"
    project_root = tmp_path / "project-plugins"
    local_root = tmp_path / "local-plugins"
    policy_root = tmp_path / "policy-plugins"

    state_store = PluginStateStore(
        state_paths={
            PluginScope.USER: tmp_path / "state" / "user.json",
            PluginScope.PROJECT: tmp_path / "state" / "project.json",
            PluginScope.LOCAL: tmp_path / "state" / "local.json",
            PluginScope.POLICY: tmp_path / "state" / "policy.json",
        }
    )

    return PluginManager(
        plugin_roots={
            PluginScope.USER: user_root,
            PluginScope.PROJECT: project_root,
            PluginScope.LOCAL: local_root,
            PluginScope.POLICY: policy_root,
        },
        state_store=state_store,
    )


@pytest.fixture(autouse=True)
def _reset_agent_runtime_state() -> None:
    registry = get_registry()
    session_ids = (
        "session-1",
        "session-abc",
        "session-skill",
        "session-agent",
        "session-other",
    )
    for session_id in session_ids:
        registry.unregister_session_agents(session_id)
        unregister_session_runtime_policies(session_id)
    yield
    for session_id in session_ids:
        registry.unregister_session_agents(session_id)
        unregister_session_runtime_policies(session_id)


def test_plugin_manager_resolves_scope_precedence(scoped_manager: PluginManager, tmp_path: Path) -> None:
    _write_plugin(tmp_path / "user-plugins", "demo-plugin", version="1.0.0")
    _write_plugin(tmp_path / "local-plugins", "demo-plugin", version="2.0.0")
    _write_plugin(tmp_path / "project-plugins", "project-only", version="1.1.0")

    _write_state(tmp_path / "state" / "user.json", ["demo-plugin"])
    _write_state(tmp_path / "state" / "local.json", ["demo-plugin"])
    _write_state(tmp_path / "state" / "project.json", ["project-only"])

    snapshot = scoped_manager.activate_session_sync("session-1", cwd=str(tmp_path))

    assert [plugin.plugin_id for plugin in snapshot.plugins] == [
        "demo-plugin",
        "project-only",
    ]
    assert snapshot.plugins[0].scope == PluginScope.LOCAL
    assert snapshot.plugins[0].manifest.version == "2.0.0"
    assert snapshot.plugins[1].scope == PluginScope.PROJECT


def test_plugin_manager_registers_session_scoped_plugin_hooks(
    scoped_manager: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "hooked-plugin",
        hooks={
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "echo plugin-hook",
                        }
                    ],
                }
            ]
        },
    )
    _write_state(tmp_path / "state" / "project.json", ["hooked-plugin"])

    scoped_manager.activate_session_sync("session-abc", cwd=str(tmp_path))

    registry = scoped_manager.hook_manager.registry
    same_session = registry.get_hooks_for_event(
        HookEvent.PRE_TOOL_USE,
        session_id="session-abc",
        match_query="Write",
    )
    other_session = registry.get_hooks_for_event(
        HookEvent.PRE_TOOL_USE,
        session_id="session-other",
        match_query="Write",
    )

    assert len(same_session) == 1
    assert same_session[0].hooks[0].command == "echo plugin-hook"
    assert other_session == []


def test_plugin_manager_parses_skills_and_binds_skill_hooks(
    scoped_manager: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "skills-plugin",
        skill_frontmatter=(
            "name: review-pr\n"
            "description: Review a pull request\n"
            "allowed-tools: Read Grep\n"
            "hooks:\n"
            "  PostToolUse:\n"
            "    - matcher: Read\n"
            "      hooks:\n"
            "        - type: command\n"
            "          command: echo skill-hook\n"
        ),
        skill_body="Review PR: $ARGUMENTS",
    )
    _write_state(tmp_path / "state" / "project.json", ["skills-plugin"])

    snapshot = scoped_manager.activate_session_sync("session-skill", cwd=str(tmp_path))
    skill = snapshot.skills["skills-plugin:review-pr"]

    rendered = skill.render(arguments=["PR-42"], session_id="session-skill")
    assert "Review PR: PR-42" in rendered
    assert skill.allowed_tools == ["Read", "Grep"]

    activation = scoped_manager.activate_skill_sync(
        session_id="session-skill",
        skill_id=skill.skill_id,
    )

    registry = scoped_manager.hook_manager.registry
    hooks = registry.get_hooks_for_event(
        HookEvent.POST_TOOL_USE,
        session_id="session-skill",
        match_query="Read",
    )

    assert activation.skill_id == skill.skill_id
    assert len(hooks) == 1
    assert hooks[0].hooks[0].command == "echo skill-hook"


def test_plugin_manager_registers_plugin_agents_for_session(
    scoped_manager: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "agent-plugin",
        agent_frontmatter=(
            "name: custom-coder\n"
            "description: Custom implementation agent\n"
            "agent-role: coder\n"
            "tools:\n"
            "  - Read\n"
            "  - Grep\n"
            "sandbox: read_only\n"
            "thinking: HIGH\n"
            "mission-graphs:\n"
            "  - coding_task\n"
        ),
        agent_body="You are a plugin-supplied coding agent.",
    )
    _write_state(tmp_path / "state" / "project.json", ["agent-plugin"])

    snapshot = scoped_manager.activate_session_sync("session-agent", cwd=str(tmp_path))
    agent_id = "agent-plugin:custom-coder"

    assert agent_id in snapshot.agents

    runtime_agent = get_agent(agent_id=agent_id, session_id="session-agent")
    runtime_policy = get_agent_runtime_policy(
        agent_id=agent_id,
        session_id="session-agent",
    )

    assert runtime_agent.agent_id == agent_id
    assert "You are a plugin-supplied coding agent." in runtime_agent.system_prompt
    assert runtime_policy.agent_role == AgentType.CODER
    assert runtime_policy.sandbox.value == "read_only"
    assert [tool.value for tool in runtime_policy.tools] == ["filesystem"]


def test_workflow_route_decision_preserves_plugin_agent_override(
    scoped_manager: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "agent-plugin",
        agent_frontmatter=(
            "name: marketplace-coder\n"
            "description: Marketplace implementation agent\n"
            "agent-role: coder\n"
            "tools:\n"
            "  - Read\n"
            "  - Grep\n"
            "mission-graphs:\n"
            "  - coding_task\n"
        ),
        agent_body="Use marketplace-specific coding rules.",
    )
    _write_state(tmp_path / "state" / "project.json", ["agent-plugin"])

    agent_id = "agent-plugin:marketplace-coder"
    scoped_manager.activate_session_sync("session-agent", cwd=str(tmp_path))
    route = WorkflowRouteDecision(
        execution_strategy=ExecutionStrategy.CHAIN,
        agent_role=AgentType.CODER,
        agent_id_override=agent_id,
        task="Implement the requested feature",
    )

    assert route.agent_id == agent_id


def test_plugin_manager_unregisters_plugin_agents_on_session_teardown(
    scoped_manager: PluginManager,
    tmp_path: Path,
) -> None:
    _write_plugin(
        tmp_path / "project-plugins",
        "agent-plugin",
        agent_frontmatter=(
            "name: custom-analyst\n"
            "description: Session-scoped analyst\n"
            "agent-role: analyst\n"
        ),
        agent_body="You are a temporary analyst.",
    )
    _write_state(tmp_path / "state" / "project.json", ["agent-plugin"])

    scoped_manager.activate_session_sync("session-agent", cwd=str(tmp_path))
    asyncio.run(scoped_manager.deactivate_session("session-agent"))

    with pytest.raises(KeyError):
        get_agent(agent_id="agent-plugin:custom-analyst", session_id="session-agent")

    with pytest.raises(KeyError):
        get_agent_runtime_policy(
            agent_id="agent-plugin:custom-analyst",
            session_id="session-agent",
        )
