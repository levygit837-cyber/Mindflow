"""Tests for MindFlow Hooks System."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from mindflow_backend.hooks import (
    HookEvent,
    HookManager,
    HookPermissionBehavior,
    HookRegistry,
    HookContext,
    HookResult,
    AggregatedHookResult,
    HookCommand,
    HookMatcher,
)


class TestHookEvent:
    """Tests for HookEvent enum."""

    def test_hook_events_exist(self) -> None:
        """All expected hook events are defined."""
        assert HookEvent.PRE_TOOL_USE == "PreToolUse"
        assert HookEvent.POST_TOOL_USE == "PostToolUse"
        assert HookEvent.POST_TOOL_USE_FAILURE == "PostToolUseFailure"
        assert HookEvent.STOP == "Stop"
        assert HookEvent.AGENT_START == "AgentStart"
        assert HookEvent.AGENT_STOP == "AgentStop"
        assert HookEvent.USER_PROMPT_SUBMIT == "UserPromptSubmit"
        assert HookEvent.SESSION_START == "SessionStart"
        assert HookEvent.PERMISSION_REQUEST == "PermissionRequest"
        assert HookEvent.PERMISSION_DENIED == "PermissionDenied"
        assert HookEvent.MISSION_START == "MissionStart"
        assert HookEvent.MISSION_STOP == "MissionStop"


class TestHookContext:
    """Tests for HookContext."""

    def test_hook_context_creation(self) -> None:
        """HookContext can be created with minimal fields."""
        ctx = HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE,
            session_id="test-session-123",
        )
        assert ctx.hook_event_name == "PreToolUse"
        assert ctx.session_id == "test-session-123"
        assert ctx.tool_name is None
        assert ctx.cwd is None

    def test_hook_context_with_tool_fields(self) -> None:
        """HookContext supports tool-specific fields."""
        ctx = HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE,
            session_id="test-session",
            tool_name="read_file",
            tool_input={"file_path": "/test.py"},
            tool_use_id="use-123",
            permission_mode="default",
        )
        assert ctx.tool_name == "read_file"
        assert ctx.tool_input == {"file_path": "/test.py"}
        assert ctx.tool_use_id == "use-123"

    def test_hook_context_to_dict(self) -> None:
        """HookContext.to_dict() serializes non-None fields."""
        ctx = HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE,
            session_id="test-session",
            tool_name="read_file",
            tool_input={"file_path": "/test.py"},
        )
        d = ctx.to_dict()
        assert d["hook_event_name"] == "PreToolUse"
        assert d["session_id"] == "test-session"
        assert d["tool_name"] == "read_file"
        assert d["tool_input"] == {"file_path": "/test.py"}
        assert "cwd" not in d  # None excluded

    def test_hook_context_mission_fields(self) -> None:
        """HookContext supports MindFlow-specific mission fields."""
        ctx = HookContext(
            hook_event_name=HookEvent.MISSION_START,
            session_id="session-1",
            mission_id="mission-abc",
            mission_name="Code Review",
        )
        assert ctx.mission_id == "mission-abc"
        assert ctx.mission_name == "Code Review"


class TestHookResult:
    """Tests for HookResult."""

    def test_hook_result_success(self) -> None:
        """Basic success result."""
        result = HookResult(
            event=HookEvent.PRE_TOOL_USE,
            command="test_command",
            status="success",
        )
        assert result.status == "success"
        assert result.behavior is None
        assert result.prevent_continuation is False

    def test_hook_result_from_response_allow(self) -> None:
        """HookResult.from_response parses allow behavior."""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Safe command",
            }
        }
        result = HookResult.from_response("PreToolUse", "cmd", response)
        assert result.behavior == HookPermissionBehavior.ALLOW
        assert result.reason == "Safe command"

    def test_hook_result_from_response_deny(self) -> None:
        """HookResult.from_response parses deny behavior."""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Dangerous command",
            }
        }
        result = HookResult.from_response("PreToolUse", "cmd", response)
        assert result.behavior == HookPermissionBehavior.DENY
        assert result.reason == "Dangerous command"

    def test_hook_result_from_response_context(self) -> None:
        """HookResult.from_response parses additionalContext."""
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "Lint issues found",
            }
        }
        result = HookResult.from_response("PostToolUse", "cmd", response)
        assert result.add_context == "Lint issues found"

    def test_hook_result_from_response_continue_false(self) -> None:
        """HookResult.from_response parses continue=false."""
        response = {
            "continue": False,
            "stopReason": "Session ending",
        }
        result = HookResult.from_response("Stop", "cmd", response)
        assert result.prevent_continuation is True
        assert result.stop_reason == "Session ending"

    def test_hook_result_from_response_plain_text(self) -> None:
        """Plain text output treated as add_context."""
        response = {"ok": True}
        # No hookSpecificOutput — result is plain success
        result = HookResult.from_response("PreToolUse", "cmd", response)
        assert result.status == "success"


class TestAggregatedHookResult:
    """Tests for AggregatedHookResult."""

    def test_aggregation_basic(self) -> None:
        """Basic aggregation of results."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd1",
                status="success",
                add_context="Context 1",
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd2",
                status="success",
                add_context="Context 2",
            ),
        ]
        agg = AggregatedHookResult.from_results(HookEvent.PRE_TOOL_USE, results)
        assert agg.event == HookEvent.PRE_TOOL_USE
        assert len(agg.additional_contexts) == 2
        assert agg.prevent_continuation is False

    def test_aggregation_blocks_on_deny(self) -> None:
        """Aggregation captures deny behavior."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd1",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="Blocked by policy",
            ),
        ]
        agg = AggregatedHookResult.from_results(HookEvent.PRE_TOOL_USE, results)
        assert agg.permission_behavior == HookPermissionBehavior.DENY
        assert agg.permission_decision_reason == "Blocked by policy"

    def test_aggregation_captures_errors(self) -> None:
        """Aggregation captures blocking errors."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd1",
                status="error",
                error="Command not found",
            ),
        ]
        agg = AggregatedHookResult.from_results(HookEvent.PRE_TOOL_USE, results)
        assert len(agg.blocking_errors) == 1
        assert agg.blocking_errors[0]["error"] == "Command not found"

    def test_aggregation_prevent_continuation(self) -> None:
        """Aggregation captures prevent_continuation."""
        results = [
            HookResult(
                event=HookEvent.STOP,
                command="cmd1",
                status="success",
                prevent_continuation=True,
                stop_reason="Hook requested stop",
            ),
        ]
        agg = AggregatedHookResult.from_results(HookEvent.STOP, results)
        assert agg.prevent_continuation is True
        assert agg.stop_reason == "Hook requested stop"

    def test_aggregation_ignores_passthrough(self) -> None:
        """Aggregation ignores passthrough behavior."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd1",
                status="success",
                behavior=HookPermissionBehavior.PASSTHROUGH,
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="cmd2",
                status="success",
                behavior=HookPermissionBehavior.ALLOW,
            ),
        ]
        agg = AggregatedHookResult.from_results(HookEvent.PRE_TOOL_USE, results)
        # passthrough is ignored, allow wins
        assert agg.permission_behavior == HookPermissionBehavior.ALLOW


class TestHookRegistry:
    """Tests for HookRegistry."""

    def test_register_config_hook(self) -> None:
        """Config hooks can be registered and retrieved."""
        registry = HookRegistry()
        cmd = HookCommand(type="command", command="echo test")
        registry.register_config_hook(
            HookEvent.PRE_TOOL_USE, "read_file", cmd
        )

        matchers = registry.get_hooks_for_event(HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 1
        assert matchers[0].matcher == "read_file"
        assert len(matchers[0].hooks) == 1
        assert matchers[0].hooks[0].command == "echo test"

    def test_register_multiple_hooks_same_matcher(self) -> None:
        """Multiple hooks for same matcher append to existing matcher."""
        registry = HookRegistry()
        cmd1 = HookCommand(type="command", command="echo 1")
        cmd2 = HookCommand(type="command", command="echo 2")
        registry.register_config_hook(HookEvent.PRE_TOOL_USE, "read_file", cmd1)
        registry.register_config_hook(HookEvent.PRE_TOOL_USE, "read_file", cmd2)

        matchers = registry.get_hooks_for_event(HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 1
        assert len(matchers[0].hooks) == 2

    def test_register_plugin_hook(self) -> None:
        """Plugin hooks can be registered and retrieved."""
        registry = HookRegistry()
        cmd = HookCommand(type="command", command="plugin-cmd")
        registry.register_plugin_hook(
            "my-plugin", HookEvent.POST_TOOL_USE, None, cmd
        )

        matchers = registry.get_hooks_for_event(HookEvent.POST_TOOL_USE)
        assert len(matchers) == 1
        assert matchers[0].hooks[0].command == "plugin-cmd"

    def test_register_agent_hook(self) -> None:
        """Agent hooks can be registered and retrieved."""
        registry = HookRegistry()
        cmd = HookCommand(type="command", command="agent-cmd")
        registry.register_agent_hook(
            "agent-123", HookEvent.AGENT_STOP, None, cmd
        )

        matchers = registry.get_hooks_for_event(
            HookEvent.AGENT_STOP, agent_id="agent-123"
        )
        assert len(matchers) == 1

    def test_unregister_agent_hooks(self) -> None:
        """Agent hooks can be unregistered."""
        registry = HookRegistry()
        cmd = HookCommand(type="command", command="agent-cmd")
        registry.register_agent_hook(
            "agent-123", HookEvent.AGENT_STOP, None, cmd
        )
        registry.unregister_agent_hooks("agent-123")

        matchers = registry.get_hooks_for_event(
            HookEvent.AGENT_STOP, agent_id="agent-123"
        )
        assert len(matchers) == 0

    def test_get_hooks_combines_sources(self) -> None:
        """get_hooks_for_event combines config + plugin hooks."""
        registry = HookRegistry()
        config_cmd = HookCommand(type="command", command="config-cmd")
        plugin_cmd = HookCommand(type="command", command="plugin-cmd")

        registry.register_config_hook(
            HookEvent.PRE_TOOL_USE, "read_file", config_cmd
        )
        registry.register_plugin_hook(
            "my-plugin", HookEvent.PRE_TOOL_USE, None, plugin_cmd
        )

        matchers = registry.get_hooks_for_event(HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 2

    def test_skip_plugins(self) -> None:
        """get_hooks_for_event can skip plugin hooks."""
        registry = HookRegistry()
        config_cmd = HookCommand(type="command", command="config-cmd")
        plugin_cmd = HookCommand(type="command", command="plugin-cmd")

        registry.register_config_hook(
            HookEvent.PRE_TOOL_USE, "read_file", config_cmd
        )
        registry.register_plugin_hook(
            "my-plugin", HookEvent.PRE_TOOL_USE, None, plugin_cmd
        )

        matchers = registry.get_hooks_for_event(
            HookEvent.PRE_TOOL_USE, skip_plugins=True
        )
        assert len(matchers) == 1
        assert matchers[0].hooks[0].command == "config-cmd"

    def test_function_hooks(self) -> None:
        """Function hooks can be registered and retrieved."""
        registry = HookRegistry()

        def my_hook(ctx: HookContext) -> HookResult:
            return HookResult(
                event=ctx.hook_event_name,
                command="<function>",
                status="success",
            )

        registry.register_function_hook(
            HookEvent.PRE_TOOL_USE, "read_file", my_hook
        )

        hooks = registry.get_function_hooks(HookEvent.PRE_TOOL_USE)
        assert len(hooks) == 1
        assert hooks[0][0] == "read_file"
        assert hooks[0][1] is my_hook

    def test_clear_all(self) -> None:
        """clear_all removes all hooks."""
        registry = HookRegistry()
        cmd = HookCommand(type="command", command="echo test")
        registry.register_config_hook(HookEvent.PRE_TOOL_USE, None, cmd)

        registry.clear_all()

        matchers = registry.get_hooks_for_event(HookEvent.PRE_TOOL_USE)
        assert len(matchers) == 0


class TestHookHelpers:
    """Tests for hooks/helpers.py functions."""

    def test_is_hook_event(self) -> None:
        """is_hook_event validates event strings."""
        from mindflow_backend.hooks.helpers import is_hook_event

        assert is_hook_event("PreToolUse") is True
        assert is_hook_event("PostToolUse") is True
        assert is_hook_event("MissionStart") is True
        assert is_hook_event("InvalidEvent") is False

    def test_validate_hook_config(self) -> None:
        """validate_hook_config catches errors."""
        from mindflow_backend.hooks.helpers import validate_hook_config

        valid = {
            "PreToolUse": [
                {"matcher": "read_file", "command": "echo test"}
            ]
        }
        assert validate_hook_config(valid) == []

        invalid = {
            "InvalidEvent": [{"command": "echo test"}]
        }
        errors = validate_hook_config(invalid)
        assert len(errors) == 1
        assert "Unknown hook event" in errors[0]

    def test_parse_hook_response(self) -> None:
        """parse_hook_response handles various inputs."""
        from mindflow_backend.hooks.helpers import parse_hook_response

        # Valid JSON
        result = parse_hook_response('{"ok": true}')
        assert result == {"ok": True}

        # Empty string
        result = parse_hook_response("")
        assert result == {"ok": True}

        # Invalid JSON
        result = parse_hook_response("not json")
        assert result["ok"] is False
        assert "Invalid JSON" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
