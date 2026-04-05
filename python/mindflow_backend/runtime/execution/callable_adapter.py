"""Adapter for converting CallableTool to ToolDefinition.

This module provides utilities to convert the new CallableTool interface
to the ToolDefinition format used by StreamingToolExecutor, enabling
migration from LangChain-based tools to the callable pattern.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.schemas.tools.callable import CallableTool, ToolResult
from mindflow_backend.schemas.tools.context import ToolContext
from mindflow_backend.runtime.execution.streaming_executor import ToolDefinition


def callable_to_tool_definition(
    callable_tool: CallableTool,
) -> ToolDefinition:
    """Convert a CallableTool to a ToolDefinition.

    This adapter bridges the gap between the new CallableTool interface
    and the ToolDefinition format used by StreamingToolExecutor.

    Args:
        callable_tool: A CallableTool instance

    Returns:
        ToolDefinition with mapped properties

    Example:
        >>> tool = FileReadTool()
        >>> definition = callable_to_tool_definition(tool)
        >>> executor = StreamingToolExecutor(
        ...     tool_definitions={tool.name: definition},
        ...     ...
        ... )
    """
    # Create a callable wrapper that invokes the CallableTool.call() method
    async def callable_wrapper(
        tool_input: dict[str, Any],
        context: Any,
    ) -> ToolResult:
        """Wrapper to invoke CallableTool.call() with proper conversion.

        Converts dict input to Pydantic model, invokes call(), and returns ToolResult.
        """
        # Import here to avoid circular dependency
        from mindflow_backend.schemas.tools.context import ToolContext as MFToolContext

        # Convert context to ToolContext if needed
        if not isinstance(context, MFToolContext):
            # If it's already a ToolContext, use it; otherwise create minimal one
            if hasattr(context, 'session_id'):
                tool_context = MFToolContext(
                    session_id=getattr(context, 'session_id', 'unknown'),
                    abort_controller=getattr(context, 'abort_controller', None),
                    cwd=getattr(context, 'cwd', None),
                    permission_mode=getattr(context, 'permission_mode', None),
                    metadata=getattr(context, 'metadata', {}),
                )
            else:
                tool_context = MFToolContext(session_id='unknown')
        else:
            tool_context = context

        # Validate and convert input dict to Pydantic model
        input_schema = callable_tool.input_schema
        try:
            validated_input = input_schema(**tool_input)
        except Exception as e:
            return ToolResult(
                data=None,
                success=False,
                error=f"Input validation failed: {e}",
                metadata={"error_code": "VALIDATION_ERROR"},
            )

        # Invoke the tool
        try:
            result = await callable_tool.call(validated_input, tool_context, on_progress=None)
            return result
        except Exception as e:
            return ToolResult(
                data=None,
                success=False,
                error=f"Tool execution failed: {e}",
                metadata={"error_code": "EXECUTION_ERROR"},
            )

    # Extract concurrency safety - need a sample input to call the method
    # Since we don't have sample input, we'll create a dummy input
    tool_metadata = callable_tool.get_metadata()
    
    # Create a dummy input for calling methods that need it
    try:
        # Try to create input with default values
        import inspect
        sig = inspect.signature(callable_tool.input_schema.__init__)
        if len(sig.parameters) == 1:  # Only self
            dummy_input = callable_tool.input_schema()
        else:
            # Create with default values if possible
            dummy_input = callable_tool.input_schema.model_construct()
        is_concurrency_safe = callable_tool.is_concurrency_safe(dummy_input)
        is_read_only = callable_tool.is_read_only(dummy_input)
    except Exception:
        # Fallback to False if we can't create dummy input
        is_concurrency_safe = False
        is_read_only = False
    
    interrupt_behavior = tool_metadata.get("interrupt_behavior", "block")
    if callable(interrupt_behavior):
        try:
            interrupt_behavior = interrupt_behavior()
        except Exception:
            interrupt_behavior = "block"

    return ToolDefinition(
        name=callable_tool.name,
        callable=callable_wrapper,
        is_concurrency_safe=is_concurrency_safe,
        description=callable_tool.description,
        is_read_only=is_read_only,
        interrupt_behavior=interrupt_behavior,
    )


def callable_tools_to_definitions(
    callable_tools: list[CallableTool],
) -> dict[str, ToolDefinition]:
    """Convert a list of CallableTools to a dict of ToolDefinitions.

    Args:
        callable_tools: List of CallableTool instances

    Returns:
        Dictionary mapping tool names to ToolDefinitions

    Example:
        >>> tools = [FileReadTool(), FileWriteTool()]
        >>> definitions = callable_tools_to_definitions(tools)
        >>> executor = StreamingToolExecutor(
        ...     tool_definitions=definitions,
        ...     ...
        ... )
    """
    return {tool.name: callable_to_tool_definition(tool) for tool in callable_tools}
