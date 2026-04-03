"""Tests for HookManager runtime semantics."""

from __future__ import annotations

import pytest

from mindflow_backend.hooks.context import HookContext
from mindflow_backend.hooks.event_broadcaster import HookEventBroadcaster
from mindflow_backend.hooks.manager import HookManager
from mindflow_backend.hooks.result import HookCommand
from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    manager = HookManager.get_instance()
    manager.registry.clear_all()

    broadcaster = HookEventBroadcaster.get_instance()
    broadcaster._handlers.clear()
    broadcaster._pending_events.clear()


@pytest.mark.asyncio
async def test_execute_post_tool_failure_uses_canonical_event_name() -> None:
    """PostToolUseFailure should execute without referencing a removed enum alias."""
    manager = HookManager.get_instance()

    results = [
        result
        async for result in manager.execute_post_tool_failure(
            tool_name="Write",
            tool_input={"file_path": "/tmp/test.txt"},
            tool_use_id="tool-1",
            error="boom",
            session_id="sess-1",
        )
    ]

    assert results == []


@pytest.mark.asyncio
async def test_pre_tool_exit_code_2_blocks_with_deny_behavior() -> None:
    """PreToolUse hooks must map exit code 2 to a deny/block decision."""
    manager = HookManager.get_instance()
    ctx = HookContext(
        hook_event_name=HookEvent.PRE_TOOL_USE,
        session_id="sess-1",
    )

    result = await manager._execute_command(
        HookCommand(type="command", command="sh -c 'exit 2'"),
        ctx,
        timeout=1.0,
    )

    assert result.status == "blocked"
    assert result.behavior == HookPermissionBehavior.DENY


@pytest.mark.asyncio
async def test_pre_compact_exit_code_2_blocks_compaction() -> None:
    """PreCompact hooks must stop compaction when the hook exits with code 2."""
    manager = HookManager.get_instance()
    ctx = HookContext(
        hook_event_name=HookEvent.PRE_COMPACT,
        session_id="sess-1",
        trigger="auto",
    )

    result = await manager._execute_command(
        HookCommand(type="command", command="sh -c 'exit 2'"),
        ctx,
        timeout=1.0,
    )

    assert result.status == "blocked"
    assert result.prevent_continuation is True
    assert result.stop_reason


@pytest.mark.asyncio
async def test_command_execution_emits_broadcast_events() -> None:
    """Hook command execution should emit lifecycle events to the broadcaster."""
    manager = HookManager.get_instance()
    broadcaster = HookEventBroadcaster.get_instance()
    ctx = HookContext(
        hook_event_name=HookEvent.PRE_TOOL_USE,
        session_id="sess-broadcast",
    )

    await manager._execute_command(
        HookCommand(type="command", command="printf '{\"ok\": true}'"),
        ctx,
        timeout=1.0,
    )

    events = broadcaster.drain_pending(lambda event: event.session_id == "sess-broadcast")
    assert [event.state.value for event in events] == ["started", "completed"]
    assert all(event.hook_event == HookEvent.PRE_TOOL_USE for event in events)
