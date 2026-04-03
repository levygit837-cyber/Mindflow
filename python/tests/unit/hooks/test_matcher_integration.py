"""Integration tests for HookMatcher with HookManager and HookRegistry."""

from __future__ import annotations

import pytest

from mindflow_backend.hooks import HookManager, HookEvent, HookContext, HookResult
from mindflow_backend.hooks.result import HookCommand


class TestHookMatcherIntegration:
    """Integration tests for pattern matching in the full hook system."""

    @pytest.fixture
    def manager(self) -> HookManager:
        """Fresh HookManager instance for each test."""
        # Create new instance (bypass singleton for testing)
        manager = HookManager()
        return manager

    @pytest.fixture
    def context(self) -> HookContext:
        """Sample HookContext for testing."""
        return HookContext(
            hook_event_name=HookEvent.PRE_TOOL_USE,
            session_id="test-session",
            tool_name="Write",
            tool_input={"file_path": "/tmp/test.py", "content": "print('hello')"},
            tool_use_id="test-tool-use-id",
        )

    @pytest.mark.asyncio
    async def test_exact_match_hook_executes(self, manager: HookManager, context: HookContext) -> None:
        """Hook with exact matcher executes for matching tool."""
        # Register hook with exact match
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "Write",
            "echo 'Hook executed'",
        )

        # Execute hooks for "Write" tool
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        # Should execute the hook
        assert len(results) == 1
        assert results[0].status == "success"

    @pytest.mark.asyncio
    async def test_exact_match_hook_does_not_execute_for_different_tool(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Hook with exact matcher does not execute for different tool."""
        # Register hook for "Write"
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "Write",
            "echo 'Hook executed'",
        )

        # Execute hooks for "Edit" tool
        context.tool_name = "Edit"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Edit",
        ):
            results.append(result)

        # Should NOT execute the hook
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_pipe_separated_matcher_executes_for_any_match(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Hook with pipe-separated matcher executes for any matching tool."""
        # Register hook with pipe-separated matcher
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "Write|Edit|Read",
            "echo 'Hook executed'",
        )

        # Test Write
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)
        assert len(results) == 1

        # Test Edit
        context.tool_name = "Edit"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Edit",
        ):
            results.append(result)
        assert len(results) == 1

        # Test Read
        context.tool_name = "Read"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Read",
        ):
            results.append(result)
        assert len(results) == 1

        # Test Bash (should NOT match)
        context.tool_name = "Bash"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Bash",
        ):
            results.append(result)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_regex_matcher_executes_for_pattern_match(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Hook with regex matcher executes for pattern-matching tools."""
        # Register hook with regex pattern
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "^Bash.*",
            "echo 'Hook executed'",
        )

        # Test Bash (should match)
        context.tool_name = "Bash"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Bash",
        ):
            results.append(result)
        assert len(results) == 1

        # Test BashCommand (should match)
        context.tool_name = "BashCommand"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="BashCommand",
        ):
            results.append(result)
        assert len(results) == 1

        # Test Write (should NOT match)
        context.tool_name = "Write"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_wildcard_matcher_executes_for_all_tools(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Hook with wildcard matcher executes for all tools."""
        # Register hook with wildcard
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "*",
            "echo 'Hook executed'",
        )

        # Test multiple tools
        for tool_name in ["Write", "Edit", "Read", "Bash", "grep_search"]:
            context.tool_name = tool_name
            results = []
            async for result in manager.execute(
                HookEvent.PRE_TOOL_USE,
                context,
                match_query=tool_name,
            ):
                results.append(result)
            assert len(results) == 1, f"Hook should execute for {tool_name}"

    @pytest.mark.asyncio
    async def test_multiple_hooks_with_different_matchers(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Multiple hooks with different matchers execute correctly."""
        # Register multiple hooks
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "Write",
            "echo 'Write hook'",
        )
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "Write|Edit",
            "echo 'Write or Edit hook'",
        )
        manager.register_command(
            HookEvent.PRE_TOOL_USE,
            "^.*$",  # Matches everything
            "echo 'Wildcard hook'",
        )

        # Execute for Write tool
        context.tool_name = "Write"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        # Should execute all 3 hooks
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_function_hook_with_matcher(self, manager: HookManager, context: HookContext) -> None:
        """Function hook with matcher executes correctly."""
        executed = []

        async def my_hook(ctx: HookContext) -> HookResult:
            executed.append(ctx.tool_name)
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        # Register function hook with matcher
        manager.register_function(
            HookEvent.PRE_TOOL_USE,
            "Write|Edit",
            my_hook,
        )

        # Execute for Write (should match)
        context.tool_name = "Write"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)
        assert len(results) == 1
        assert "Write" in executed

        # Execute for Bash (should NOT match)
        context.tool_name = "Bash"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Bash",
        ):
            results.append(result)
        assert len(results) == 0
