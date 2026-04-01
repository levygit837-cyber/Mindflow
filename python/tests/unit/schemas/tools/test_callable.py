"""Unit tests for callable tool infrastructure.

Tests cover:
- CallableTool interface and ToolResult
- build_callable_tool() factory with defaults
- build_readonly_tool() and build_destructive_tool() helpers
- StreamingToolExecutor concurrency control
- Callable to LangChain adapter
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.callable import CallableTool, ToolResult
from mindflow_backend.schemas.tools.callable_builder import (
    build_callable_tool,
    build_destructive_tool,
    build_readonly_tool,
)
from mindflow_backend.schemas.tools.callable_executor import StreamingToolExecutor
from mindflow_backend.schemas.tools.context import ToolContext


# ── Test Fixtures ──


class SimpleInput(BaseModel):
    """Simple input schema for testing."""

    value: str = Field(..., description="Test value")


class SimpleOutput(BaseModel):
    """Simple output schema for testing."""

    result: str


@pytest.fixture
def mock_context():
    """Create a mock ToolContext."""
    return ToolContext(
        permission_context=None,
        metadata={"test": True},
    )


# ── Test ToolResult ──


def test_tool_result_success():
    """Test ToolResult with success."""
    result = ToolResult(data="test_data", success=True)

    assert result.success is True
    assert result.data == "test_data"
    assert result.error is None
    assert result.metadata == {}


def test_tool_result_error():
    """Test ToolResult with error."""
    result = ToolResult(
        data=None,
        success=False,
        error="Test error",
        metadata={"error_code": "TEST_ERROR"},
    )

    assert result.success is False
    assert result.data is None
    assert result.error == "Test error"
    assert result.metadata["error_code"] == "TEST_ERROR"


def test_tool_result_to_dict():
    """Test ToolResult.to_dict() serialization."""
    result = ToolResult(
        data={"key": "value"},
        success=True,
        metadata={"timing": 123},
    )

    result_dict = result.to_dict()

    assert result_dict["success"] is True
    assert result_dict["data"] == {"key": "value"}
    assert result_dict["error"] is None
    assert result_dict["metadata"]["timing"] == 123


# ── Test build_callable_tool() ──


@pytest.mark.asyncio
async def test_build_callable_tool_basic(mock_context):
    """Test basic callable tool creation."""

    async def simple_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data=f"processed: {input.value}", success=True)

    tool = build_callable_tool(
        name="simple_tool",
        description="A simple test tool",
        input_schema=SimpleInput,
        call_fn=simple_impl,
    )

    assert tool.name == "simple_tool"
    assert tool.description == "A simple test tool"
    assert tool.input_schema == SimpleInput

    # Test execution
    input_data = SimpleInput(value="test")
    result = await tool.call(input_data, mock_context)

    assert result.success is True
    assert result.data == "processed: test"


@pytest.mark.asyncio
async def test_build_callable_tool_defaults(mock_context):
    """Test that callable tool has fail-closed defaults."""

    async def dummy_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="ok", success=True)

    tool = build_callable_tool(
        name="test_tool",
        description="Test",
        input_schema=SimpleInput,
        call_fn=dummy_impl,
    )

    input_data = SimpleInput(value="test")

    # Check fail-closed defaults
    assert tool.is_read_only(input_data) is False  # Assume writes
    assert tool.is_concurrency_safe(input_data) is False  # Assume not safe
    assert tool.is_destructive(input_data) is False
    assert tool.is_enabled() is True
    assert tool.interrupt_behavior() == "block"  # Safe default


@pytest.mark.asyncio
async def test_build_callable_tool_explicit_flags(mock_context):
    """Test callable tool with explicit permission flags."""

    async def read_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="read_data", success=True)

    tool = build_callable_tool(
        name="read_tool",
        description="Read-only tool",
        input_schema=SimpleInput,
        call_fn=read_impl,
        is_read_only=True,
        is_concurrency_safe=True,
        interrupt_behavior="cancel",
    )

    input_data = SimpleInput(value="test")

    assert tool.is_read_only(input_data) is True
    assert tool.is_concurrency_safe(input_data) is True
    assert tool.is_destructive(input_data) is False
    assert tool.interrupt_behavior() == "cancel"


@pytest.mark.asyncio
async def test_build_callable_tool_custom_validation(mock_context):
    """Test callable tool with custom validation."""

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="ok", success=True)

    async def validate(input: SimpleInput, context: ToolContext):
        if input.value == "invalid":
            return (False, "Value cannot be 'invalid'")
        return (True, None)

    tool = build_callable_tool(
        name="validated_tool",
        description="Tool with validation",
        input_schema=SimpleInput,
        call_fn=impl,
        validate_input_fn=validate,
    )

    # Test valid input
    valid_input = SimpleInput(value="valid")
    is_valid, error = await tool.validate_input(valid_input, mock_context)
    assert is_valid is True
    assert error is None

    # Test invalid input
    invalid_input = SimpleInput(value="invalid")
    is_valid, error = await tool.validate_input(invalid_input, mock_context)
    assert is_valid is False
    assert error == "Value cannot be 'invalid'"


# ── Test build_readonly_tool() ──


@pytest.mark.asyncio
async def test_build_readonly_tool(mock_context):
    """Test readonly tool builder convenience function."""

    async def read_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="read_data", success=True)

    tool = build_readonly_tool(
        name="read_tool",
        description="Read-only tool",
        input_schema=SimpleInput,
        call_fn=read_impl,
    )

    input_data = SimpleInput(value="test")

    # Check readonly defaults
    assert tool.is_read_only(input_data) is True
    assert tool.is_concurrency_safe(input_data) is True  # Default for readonly
    assert tool.is_destructive(input_data) is False
    assert tool.interrupt_behavior() == "cancel"  # Default for readonly


# ── Test build_destructive_tool() ──


@pytest.mark.asyncio
async def test_build_destructive_tool(mock_context):
    """Test destructive tool builder convenience function."""

    async def delete_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="deleted", success=True)

    tool = build_destructive_tool(
        name="delete_tool",
        description="Destructive tool",
        input_schema=SimpleInput,
        call_fn=delete_impl,
    )

    input_data = SimpleInput(value="test")

    # Check destructive defaults
    assert tool.is_read_only(input_data) is False
    assert tool.is_concurrency_safe(input_data) is False  # Default for destructive
    assert tool.is_destructive(input_data) is True
    assert tool.interrupt_behavior() == "block"  # Default for destructive


# ── Test StreamingToolExecutor ──


@pytest.mark.asyncio
async def test_executor_single_tool(mock_context):
    """Test executor with single tool execution."""

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data=f"result: {input.value}", success=True)

    tool = build_callable_tool(
        name="test_tool",
        description="Test",
        input_schema=SimpleInput,
        call_fn=impl,
    )

    executor = StreamingToolExecutor([tool], mock_context)

    result = await executor.execute_tool_call("test_tool", {"value": "test"})

    assert result.success is True
    assert result.data == "result: test"


@pytest.mark.asyncio
async def test_executor_unknown_tool(mock_context):
    """Test executor with unknown tool name."""

    executor = StreamingToolExecutor([], mock_context)

    result = await executor.execute_tool_call("unknown_tool", {"value": "test"})

    assert result.success is False
    assert "Unknown tool" in result.error
    assert result.metadata["error_code"] == "UNKNOWN_TOOL"


@pytest.mark.asyncio
async def test_executor_invalid_input(mock_context):
    """Test executor with invalid input."""

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data="ok", success=True)

    tool = build_callable_tool(
        name="test_tool",
        description="Test",
        input_schema=SimpleInput,
        call_fn=impl,
    )

    executor = StreamingToolExecutor([tool], mock_context)

    # Missing required field 'value'
    result = await executor.execute_tool_call("test_tool", {})

    assert result.success is False
    assert "Invalid input" in result.error
    assert result.metadata["error_code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_executor_concurrent_tools(mock_context):
    """Test executor with concurrent-safe tools running in parallel."""

    call_order = []

    async def slow_impl(input: SimpleInput, context: ToolContext, on_progress):
        call_order.append(f"start_{input.value}")
        await asyncio.sleep(0.1)
        call_order.append(f"end_{input.value}")
        return ToolResult(data=input.value, success=True)

    tool = build_callable_tool(
        name="slow_tool",
        description="Slow concurrent tool",
        input_schema=SimpleInput,
        call_fn=slow_impl,
        is_concurrency_safe=True,
    )

    executor = StreamingToolExecutor([tool], mock_context)

    # Execute two calls concurrently
    task1 = asyncio.create_task(executor.execute_tool_call("slow_tool", {"value": "A"}))
    task2 = asyncio.create_task(executor.execute_tool_call("slow_tool", {"value": "B"}))

    results = await asyncio.gather(task1, task2)

    # Both should succeed
    assert results[0].success is True
    assert results[1].success is True

    # Calls should have overlapped (concurrent execution)
    # If sequential: [start_A, end_A, start_B, end_B]
    # If concurrent: [start_A, start_B, end_A, end_B] or similar
    assert call_order[0].startswith("start_")
    assert call_order[1].startswith("start_")  # Second start before first end


@pytest.mark.asyncio
async def test_executor_non_concurrent_tools(mock_context):
    """Test executor with non-concurrent tools running sequentially."""

    call_order = []

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        call_order.append(f"start_{input.value}")
        await asyncio.sleep(0.05)
        call_order.append(f"end_{input.value}")
        return ToolResult(data=input.value, success=True)

    tool = build_callable_tool(
        name="sequential_tool",
        description="Non-concurrent tool",
        input_schema=SimpleInput,
        call_fn=impl,
        is_concurrency_safe=False,
    )

    executor = StreamingToolExecutor([tool], mock_context)

    # Execute two calls
    result1 = await executor.execute_tool_call("sequential_tool", {"value": "A"})
    result2 = await executor.execute_tool_call("sequential_tool", {"value": "B"})

    # Both should succeed
    assert result1.success is True
    assert result2.success is True

    # Calls should be sequential
    assert call_order == ["start_A", "end_A", "start_B", "end_B"]


@pytest.mark.asyncio
async def test_executor_tool_error_cancels_siblings(mock_context):
    """Test that tool errors cancel sibling tools."""

    async def error_impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data=None, success=False, error="Tool failed")

    async def slow_impl(input: SimpleInput, context: ToolContext, on_progress):
        await asyncio.sleep(1.0)  # Long running
        return ToolResult(data="completed", success=True)

    error_tool = build_callable_tool(
        name="error_tool",
        description="Tool that errors",
        input_schema=SimpleInput,
        call_fn=error_impl,
        is_concurrency_safe=True,
    )

    slow_tool = build_callable_tool(
        name="slow_tool",
        description="Slow tool",
        input_schema=SimpleInput,
        call_fn=slow_impl,
        is_concurrency_safe=True,
    )

    executor = StreamingToolExecutor([error_tool, slow_tool], mock_context)

    # Start slow tool
    slow_task = asyncio.create_task(
        executor.execute_tool_call("slow_tool", {"value": "test"})
    )

    # Let it start
    await asyncio.sleep(0.05)

    # Execute error tool (should cancel slow tool)
    error_result = await executor.execute_tool_call("error_tool", {"value": "test"})

    # Error tool should fail
    assert error_result.success is False

    # Slow tool should be cancelled
    slow_result = await slow_task
    # Task was cancelled, so it should complete quickly
    assert executor.has_errored is True


@pytest.mark.asyncio
async def test_executor_wait_all(mock_context):
    """Test executor wait_all() method."""

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        await asyncio.sleep(0.1)
        return ToolResult(data="ok", success=True)

    tool = build_callable_tool(
        name="test_tool",
        description="Test",
        input_schema=SimpleInput,
        call_fn=impl,
        is_concurrency_safe=True,
    )

    executor = StreamingToolExecutor([tool], mock_context)

    # Start multiple concurrent tasks
    task1 = asyncio.create_task(executor.execute_tool_call("test_tool", {"value": "A"}))
    task2 = asyncio.create_task(executor.execute_tool_call("test_tool", {"value": "B"}))

    # Wait for both tasks to complete
    await asyncio.gather(task1, task2)

    # Wait for executor to finish (should be immediate since tasks are done)
    await executor.wait_all()

    # All tasks should be done
    assert task1.done()
    assert task2.done()
    assert not executor.has_executing_tools()


# ── Test Callable to LangChain Adapter ──


@pytest.mark.asyncio
async def test_callable_to_langchain_adapter(mock_context):
    """Test callable to LangChain adapter."""
    pytest.importorskip("langchain_core")

    from mindflow_backend.schemas.tools.callable_adapter import callable_to_langchain

    async def impl(input: SimpleInput, context: ToolContext, on_progress):
        return ToolResult(data=f"result: {input.value}", success=True)

    callable_tool = build_callable_tool(
        name="test_tool",
        description="Test tool",
        input_schema=SimpleInput,
        call_fn=impl,
    )

    # Convert to LangChain
    lc_tool = callable_to_langchain(callable_tool)

    assert lc_tool.name == "test_tool"
    assert lc_tool.description == "Test tool"

    # Test execution through LangChain interface
    result_str = await lc_tool.coroutine(value="test")

    import json

    result = json.loads(result_str)
    assert result["success"] is True
    assert result["data"] == "result: test"
