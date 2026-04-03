"""Tests for HookResultProcessor."""

from __future__ import annotations

import pytest

from mindflow_backend.hooks.processor import HookResultProcessor
from mindflow_backend.hooks.result import HookResult
from mindflow_backend.hooks.types import HookEvent, HookPermissionBehavior


class TestHookResultProcessorPreTool:
    """Tests for process_pre_tool_results()."""

    def test_process_empty_results(self) -> None:
        """Empty results list returns original input."""
        original_input = {"file_path": "/tmp/test.py", "content": "hello"}
        processed = HookResultProcessor.process_pre_tool_results([], original_input)

        assert processed["allowed"] is True
        assert processed["reason"] is None
        assert processed["updated_input"] == original_input
        assert processed["additional_context"] == []

    def test_process_allow_behavior(self) -> None:
        """Allow behavior permits execution."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.ALLOW,
            )
        ]
        processed = HookResultProcessor.process_pre_tool_results(results, {})

        assert processed["allowed"] is True
        assert processed["reason"] is None

    def test_process_deny_behavior(self) -> None:
        """Deny behavior blocks execution."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="Dangerous command",
            )
        ]
        processed = HookResultProcessor.process_pre_tool_results(results, {})

        assert processed["allowed"] is False
        assert processed["reason"] == "Dangerous command"

    def test_process_deny_stops_processing(self) -> None:
        """Deny behavior stops processing remaining hooks."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.ALLOW,
                updated_input={"file": "first.py"},
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook2",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="Blocked",
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook3",
                status="success",
                updated_input={"file": "third.py"},  # Should not be applied
            ),
        ]
        processed = HookResultProcessor.process_pre_tool_results(results, {})

        assert processed["allowed"] is False
        assert processed["reason"] == "Blocked"
        # Only first hook's update should be applied
        assert processed["updated_input"]["file"] == "first.py"

    def test_process_updated_input_sequential(self) -> None:
        """Updated input is applied sequentially."""
        original_input = {"file": "original.py", "mode": "read"}
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                updated_input={"file": "first.py"},
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook2",
                status="success",
                updated_input={"mode": "write"},
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook3",
                status="success",
                updated_input={"file": "final.py"},  # Overwrites previous
            ),
        ]
        processed = HookResultProcessor.process_pre_tool_results(results, original_input)

        assert processed["updated_input"]["file"] == "final.py"
        assert processed["updated_input"]["mode"] == "write"

    def test_process_additional_context(self) -> None:
        """Additional context is collected from all hooks."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                add_context="Lint passed",
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook2",
                status="success",
                add_context="Tests passed",
            ),
        ]
        processed = HookResultProcessor.process_pre_tool_results(results, {})

        assert len(processed["additional_context"]) == 2
        assert "Lint passed" in processed["additional_context"]
        assert "Tests passed" in processed["additional_context"]


class TestHookResultProcessorPostTool:
    """Tests for process_post_tool_results()."""

    def test_process_empty_results(self) -> None:
        """Empty results list returns original output."""
        original_output = {"status": "success", "data": "hello"}
        processed = HookResultProcessor.process_post_tool_results([], original_output)

        assert processed["updated_output"] == original_output
        assert processed["additional_context"] == []
        assert processed["watch_paths"] == []

    def test_process_updated_output_last_wins(self) -> None:
        """Last updated_mcp_tool_output wins."""
        original_output = {"formatted": False}
        results = [
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook1",
                status="success",
                updated_mcp_tool_output={"formatted": True, "linted": False},
            ),
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook2",
                status="success",
                updated_mcp_tool_output={"formatted": True, "linted": True},
            ),
        ]
        processed = HookResultProcessor.process_post_tool_results(results, original_output)

        # Last hook's output should win
        assert processed["updated_output"]["formatted"] is True
        assert processed["updated_output"]["linted"] is True

    def test_process_additional_context(self) -> None:
        """Additional context is collected from all hooks."""
        results = [
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook1",
                status="success",
                add_context="Formatted with black",
            ),
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook2",
                status="success",
                add_context="Linted with ruff",
            ),
        ]
        processed = HookResultProcessor.process_post_tool_results(results, {})

        assert len(processed["additional_context"]) == 2
        assert "Formatted with black" in processed["additional_context"]
        assert "Linted with ruff" in processed["additional_context"]

    def test_process_watch_paths(self) -> None:
        """Watch paths are collected from all hooks."""
        results = [
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook1",
                status="success",
                watch_paths=["/tmp/file1.py", "/tmp/file2.py"],
            ),
            HookResult(
                event=HookEvent.POST_TOOL_USE,
                command="hook2",
                status="success",
                watch_paths=["/tmp/file3.py"],
            ),
        ]
        processed = HookResultProcessor.process_post_tool_results(results, {})

        assert len(processed["watch_paths"]) == 3
        assert "/tmp/file1.py" in processed["watch_paths"]
        assert "/tmp/file2.py" in processed["watch_paths"]
        assert "/tmp/file3.py" in processed["watch_paths"]


class TestHookResultProcessorBlockExecution:
    """Tests for should_block_execution()."""

    def test_no_block_with_empty_results(self) -> None:
        """Empty results do not block."""
        blocked, reason = HookResultProcessor.should_block_execution([])
        assert blocked is False
        assert reason is None

    def test_no_block_with_allow(self) -> None:
        """Allow behavior does not block."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.ALLOW,
            )
        ]
        blocked, reason = HookResultProcessor.should_block_execution(results)
        assert blocked is False
        assert reason is None

    def test_block_with_deny(self) -> None:
        """Deny behavior blocks execution."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="Dangerous command",
            )
        ]
        blocked, reason = HookResultProcessor.should_block_execution(results)
        assert blocked is True
        assert reason == "Dangerous command"

    def test_block_with_prevent_continuation(self) -> None:
        """prevent_continuation blocks execution."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                prevent_continuation=True,
                stop_reason="Hook requested stop",
            )
        ]
        blocked, reason = HookResultProcessor.should_block_execution(results)
        assert blocked is True
        assert reason == "Hook requested stop"

    def test_block_with_first_deny(self) -> None:
        """First deny blocks even if later hooks allow."""
        results = [
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook1",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="First deny",
            ),
            HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="hook2",
                status="success",
                behavior=HookPermissionBehavior.ALLOW,
            ),
        ]
        blocked, reason = HookResultProcessor.should_block_execution(results)
        assert blocked is True
        assert reason == "First deny"


class TestHookResultProcessorMergeContexts:
    """Tests for merge_additional_contexts()."""

    def test_merge_empty_list(self) -> None:
        """Empty list returns None."""
        merged = HookResultProcessor.merge_additional_contexts([])
        assert merged is None

    def test_merge_single_context(self) -> None:
        """Single context returns as-is."""
        merged = HookResultProcessor.merge_additional_contexts(["Context 1"])
        assert merged == "Context 1"

    def test_merge_multiple_contexts(self) -> None:
        """Multiple contexts are joined with newlines."""
        contexts = ["Context 1", "Context 2", "Context 3"]
        merged = HookResultProcessor.merge_additional_contexts(contexts)
        assert merged == "Context 1\nContext 2\nContext 3"
