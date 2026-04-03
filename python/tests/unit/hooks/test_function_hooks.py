"""Tests for Function Hooks - Python callback hooks."""

from __future__ import annotations

import pytest

from mindflow_backend.hooks import HookManager, HookEvent, HookContext, HookResult
from mindflow_backend.hooks.types import HookPermissionBehavior


class TestFunctionHooks:
    """Tests for function hook registration and execution."""

    @pytest.fixture
    def manager(self) -> HookManager:
        """Fresh HookManager instance for each test."""
        return HookManager()

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
    async def test_register_function_hook(self, manager: HookManager) -> None:
        """Function hook can be registered."""
        executed = []

        async def my_hook(ctx: HookContext) -> HookResult:
            executed.append(ctx.tool_name)
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        # Register function hook
        manager.register_function(
            HookEvent.PRE_TOOL_USE,
            "Write",
            my_hook,
        )

        # Verify it's registered
        function_hooks = manager.registry.get_function_hooks(HookEvent.PRE_TOOL_USE)
        assert len(function_hooks) == 1
        assert function_hooks[0][0] == "Write"

    @pytest.mark.asyncio
    async def test_function_hook_executes(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook executes when event fires."""
        executed = []

        async def my_hook(ctx: HookContext) -> HookResult:
            executed.append(ctx.tool_name)
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", my_hook)

        # Execute hooks
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].status == "success"
        assert "Write" in executed

    @pytest.mark.asyncio
    async def test_function_hook_can_deny(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook can deny execution."""

        async def deny_hook(ctx: HookContext) -> HookResult:
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
                behavior=HookPermissionBehavior.DENY,
                reason="Blocked by function hook",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", deny_hook)

        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].behavior == HookPermissionBehavior.DENY
        assert results[0].reason == "Blocked by function hook"

    @pytest.mark.asyncio
    async def test_function_hook_can_modify_input(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook can modify tool input."""

        async def modify_hook(ctx: HookContext) -> HookResult:
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
                updated_input={"file_path": "/tmp/modified.py"},
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", modify_hook)

        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].updated_input is not None
        assert results[0].updated_input["file_path"] == "/tmp/modified.py"

    @pytest.mark.asyncio
    async def test_function_hook_can_add_context(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook can add context to prompt."""

        async def context_hook(ctx: HookContext) -> HookResult:
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
                add_context="File validated successfully",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", context_hook)

        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].add_context == "File validated successfully"

    @pytest.mark.asyncio
    async def test_function_hook_with_wildcard_matcher(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook with None matcher executes for all tools."""
        executed = []

        async def wildcard_hook(ctx: HookContext) -> HookResult:
            executed.append(ctx.tool_name)
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, None, wildcard_hook)

        # Test with different tools
        for tool_name in ["Write", "Edit", "Read"]:
            context.tool_name = tool_name
            results = []
            async for result in manager.execute(
                HookEvent.PRE_TOOL_USE,
                context,
                match_query=tool_name,
            ):
                results.append(result)
            assert len(results) == 1

        assert len(executed) == 3

    @pytest.mark.asyncio
    async def test_function_hook_with_regex_matcher(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook with regex matcher works correctly."""
        executed = []

        async def regex_hook(ctx: HookContext) -> HookResult:
            executed.append(ctx.tool_name)
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "^Write.*", regex_hook)

        # Should match Write
        context.tool_name = "Write"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)
        assert len(results) == 1

        # Should not match Edit
        context.tool_name = "Edit"
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Edit",
        ):
            results.append(result)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_function_hook_timeout(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook respects timeout."""
        import asyncio

        async def slow_hook(ctx: HookContext) -> HookResult:
            await asyncio.sleep(10)  # Sleep longer than timeout
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", slow_hook)

        # Execute with short timeout
        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
            timeout=0.1,  # Very short timeout
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].status == "timeout"

    @pytest.mark.asyncio
    async def test_multiple_function_hooks(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Multiple function hooks execute in order."""
        execution_order = []

        async def hook1(ctx: HookContext) -> HookResult:
            execution_order.append("hook1")
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        async def hook2(ctx: HookContext) -> HookResult:
            execution_order.append("hook2")
            return HookResult(
                event=HookEvent.PRE_TOOL_USE,
                command="<function>",
                status="success",
            )

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", hook1)
        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", hook2)

        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 2
        assert execution_order == ["hook1", "hook2"]

    @pytest.mark.asyncio
    async def test_function_hook_exception_handling(
        self, manager: HookManager, context: HookContext
    ) -> None:
        """Function hook exceptions are caught and returned as errors."""

        async def failing_hook(ctx: HookContext) -> HookResult:
            raise ValueError("Hook failed")

        manager.register_function(HookEvent.PRE_TOOL_USE, "Write", failing_hook)

        results = []
        async for result in manager.execute(
            HookEvent.PRE_TOOL_USE,
            context,
            match_query="Write",
        ):
            results.append(result)

        assert len(results) == 1
        assert results[0].status == "error"
        assert "Hook failed" in results[0].error
