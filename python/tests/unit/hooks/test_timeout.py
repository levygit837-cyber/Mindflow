"""Tests for TimeoutConfig and AbortController."""

from __future__ import annotations

import asyncio

import pytest

from mindflow_backend.hooks.timeout import (
    TimeoutConfig,
    AbortController,
    DEFAULT_HOOK_TIMEOUT,
    TOOL_HOOK_TIMEOUT,
    SESSION_HOOK_TIMEOUT,
    COMPACT_HOOK_TIMEOUT,
)


class TestTimeoutConfig:
    """Tests for TimeoutConfig.get_timeout()."""

    def test_get_timeout_with_hook_timeout(self) -> None:
        """Hook-specific timeout takes precedence."""
        assert TimeoutConfig.get_timeout("PreToolUse", 10.0) == 10.0
        assert TimeoutConfig.get_timeout("PostToolUse", 5.0) == 5.0
        assert TimeoutConfig.get_timeout("SessionStart", 15.0) == 15.0

    def test_get_timeout_tool_events(self) -> None:
        """Tool events use TOOL_HOOK_TIMEOUT."""
        assert TimeoutConfig.get_timeout("PreToolUse", None) == TOOL_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("PostToolUse", None) == TOOL_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("PostToolUseFailure", None) == TOOL_HOOK_TIMEOUT

    def test_get_timeout_session_events(self) -> None:
        """Session events use SESSION_HOOK_TIMEOUT."""
        assert TimeoutConfig.get_timeout("SessionStart", None) == SESSION_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("SessionEnd", None) == SESSION_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("Stop", None) == SESSION_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("StopFailure", None) == SESSION_HOOK_TIMEOUT

    def test_get_timeout_compact_events(self) -> None:
        """Compact events use COMPACT_HOOK_TIMEOUT."""
        assert TimeoutConfig.get_timeout("PreCompact", None) == COMPACT_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("PostCompact", None) == COMPACT_HOOK_TIMEOUT

    def test_get_timeout_default_fallback(self) -> None:
        """Unknown events use DEFAULT_HOOK_TIMEOUT."""
        assert TimeoutConfig.get_timeout("UnknownEvent", None) == DEFAULT_HOOK_TIMEOUT
        assert TimeoutConfig.get_timeout("CustomEvent", None) == DEFAULT_HOOK_TIMEOUT

    @pytest.mark.asyncio
    async def test_create_timeout_task_sets_event(self) -> None:
        """Timeout task sets abort_event after timeout."""
        abort_event = asyncio.Event()

        # Create timeout task with short timeout
        task = asyncio.create_task(
            TimeoutConfig.create_timeout_task(0.1, abort_event)
        )

        # Event should not be set immediately
        assert not abort_event.is_set()

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Event should be set now
        assert abort_event.is_set()

        # Cleanup
        task.cancel()

    @pytest.mark.asyncio
    async def test_create_timeout_task_cancellable(self) -> None:
        """Timeout task can be cancelled before timeout."""
        abort_event = asyncio.Event()

        # Create timeout task with long timeout
        task = asyncio.create_task(
            TimeoutConfig.create_timeout_task(10.0, abort_event)
        )

        # Cancel immediately
        task.cancel()

        # Wait a bit
        await asyncio.sleep(0.1)

        # Event should NOT be set
        assert not abort_event.is_set()

    @pytest.mark.asyncio
    async def test_create_combined_abort_signal(self) -> None:
        """Combined abort signal creates event and timeout task."""
        abort_event, timeout_task = TimeoutConfig.create_combined_abort_signal(
            manual_signal=None,
            timeout=0.1,
        )

        # Event should not be set immediately
        assert not abort_event.is_set()

        # Wait for timeout
        await asyncio.sleep(0.15)

        # Event should be set now
        assert abort_event.is_set()

        # Cleanup
        timeout_task.cancel()

    @pytest.mark.asyncio
    async def test_create_combined_abort_signal_with_manual_signal(self) -> None:
        """Combined abort signal respects manual signal."""
        manual_signal = asyncio.Event()
        manual_signal.set()  # Already set

        abort_event, timeout_task = TimeoutConfig.create_combined_abort_signal(
            manual_signal=manual_signal,
            timeout=10.0,
        )

        # Event should be set immediately
        assert abort_event.is_set()

        # Cleanup
        timeout_task.cancel()


class TestAbortController:
    """Tests for AbortController."""

    def test_abort_controller_initialization(self) -> None:
        """AbortController initializes correctly."""
        controller = AbortController()
        assert not controller.is_aborted()
        assert isinstance(controller.signal, asyncio.Event)

    def test_abort_controller_abort(self) -> None:
        """abort() sets the signal."""
        controller = AbortController()
        controller.abort()
        assert controller.is_aborted()
        assert controller.signal.is_set()

    def test_abort_controller_check_or_raise(self) -> None:
        """check_or_raise() raises when aborted."""
        controller = AbortController()

        # Should not raise when not aborted
        controller.check_or_raise()

        # Should raise when aborted
        controller.abort()
        with pytest.raises(asyncio.CancelledError):
            controller.check_or_raise()

    def test_abort_controller_parent_child(self) -> None:
        """Child controller inherits parent abort."""
        parent = AbortController()
        child = AbortController(parent=parent)

        # Neither aborted initially
        assert not parent.is_aborted()
        assert not child.is_aborted()

        # Abort parent
        parent.abort()

        # Both should be aborted
        assert parent.is_aborted()
        assert child.is_aborted()

    def test_abort_controller_child_propagation(self) -> None:
        """Aborting parent propagates to all children."""
        parent = AbortController()
        child1 = AbortController(parent=parent)
        child2 = AbortController(parent=parent)
        grandchild = AbortController(parent=child1)

        # Abort parent
        parent.abort()

        # All should be aborted
        assert parent.is_aborted()
        assert child1.is_aborted()
        assert child2.is_aborted()
        assert grandchild.is_aborted()

    def test_abort_controller_child_independent(self) -> None:
        """Aborting child does not affect parent."""
        parent = AbortController()
        child = AbortController(parent=parent)

        # Abort child
        child.abort()

        # Only child should be aborted
        assert child.is_aborted()
        assert not parent.is_aborted()

    def test_abort_controller_multiple_children(self) -> None:
        """Parent can have multiple children."""
        parent = AbortController()
        child1 = AbortController(parent=parent)
        child2 = AbortController(parent=parent)
        child3 = AbortController(parent=parent)

        # Abort parent
        parent.abort()

        # All children should be aborted
        assert child1.is_aborted()
        assert child2.is_aborted()
        assert child3.is_aborted()
