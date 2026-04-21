"""Runtime execution exports."""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "BackgroundTaskHandle",
    "BackgroundTaskManager",
    "StreamingToolExecutor",
    "ToolBatch",
    "ToolCallable",
    "ToolDefinition",
    "ToolExecutionConfig",
    "ToolUseContext",
    "callable_to_tool_definition",
    "callable_tools_to_definitions",
    "partition_tool_calls",
]

_LAZY_ATTRS: dict[str, tuple[str, str]] = {
    "BackgroundTaskHandle": (
        "mindflow_backend.runtime.execution.background_task_manager",
        "BackgroundTaskHandle",
    ),
    "BackgroundTaskManager": (
        "mindflow_backend.runtime.execution.background_task_manager",
        "BackgroundTaskManager",
    ),
    "callable_to_tool_definition": (
        "mindflow_backend.runtime.execution.callable_adapter",
        "callable_to_tool_definition",
    ),
    "callable_tools_to_definitions": (
        "mindflow_backend.runtime.execution.callable_adapter",
        "callable_tools_to_definitions",
    ),
    "StreamingToolExecutor": (
        "mindflow_backend.runtime.execution.streaming_executor",
        "StreamingToolExecutor",
    ),
    "ToolDefinition": (
        "mindflow_backend.runtime.execution.streaming_executor",
        "ToolDefinition",
    ),
    "ToolCallable": (
        "mindflow_backend.runtime.execution.streaming_executor",
        "ToolCallable",
    ),
    "ToolUseContext": (
        "mindflow_backend.runtime.execution.streaming_executor",
        "ToolUseContext",
    ),
    "partition_tool_calls": (
        "mindflow_backend.runtime.execution.tool_partition",
        "partition_tool_calls",
    ),
    "ToolBatch": ("mindflow_backend.runtime.execution.tool_partition", "ToolBatch"),
    "ToolExecutionConfig": (
        "mindflow_backend.runtime.execution.tool_config",
        "ToolExecutionConfig",
    ),
}


def __getattr__(name: str):
    try:
        module_name, attr_name = _LAZY_ATTRS[name]
    except KeyError as exc:  # pragma: no cover - Python fallback path
        raise AttributeError(name) from exc
    module = import_module(module_name)
    return getattr(module, attr_name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
