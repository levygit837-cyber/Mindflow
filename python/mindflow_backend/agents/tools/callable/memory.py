"""Callable memory tools backed by the canonical memory helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools import CallableToolResult, ToolContext, build_callable_tool


class StoreFactInput(BaseModel):
    content: str = Field(min_length=1)
    fact_type: str = "fact"
    key: str = ""
    namespace: str = "general"


class SearchFactsInput(BaseModel):
    query: str = Field(min_length=1)
    fact_type: str = "all"
    limit: int = Field(default=5, ge=1, le=50)


class RetrieveTaskContextInput(BaseModel):
    query: str = Field(min_length=1)
    session_id: str = ""
    limit: int = Field(default=5, ge=1, le=50)


class RecallSessionMemoryInput(BaseModel):
    query: str = Field(min_length=1)
    cross_session: bool = False
    limit: int = Field(default=5, ge=1, le=50)


def _configure_memory_tool(tool: Any, context: ToolContext) -> Any:
    if context.root_dir and hasattr(tool, "root_dir"):
        tool.root_dir = context.root_dir
    if context.session_id and hasattr(tool, "session_id"):
        tool.session_id = context.session_id
    if context.execution_id and hasattr(tool, "execution_id"):
        tool.execution_id = context.execution_id
    return tool


def _resolve_memory_tool_class(name: str) -> type[Any]:
    module = import_module("mindflow_backend.agents.tools.integration.memory_tools")
    return getattr(module, name)


async def _wrap_memory_result(
    tool_factory_name: str,
    payload: BaseModel,
    context: ToolContext,
) -> CallableToolResult[dict[str, Any]]:
    tool_factory = _resolve_memory_tool_class(tool_factory_name)
    tool = _configure_memory_tool(tool_factory(), context)
    result = await tool.execute(**payload.model_dump())
    success = bool(result.get("success", True)) if isinstance(result, dict) else True
    return CallableToolResult(
        success=success,
        data=result if isinstance(result, dict) else {"output": result},
        error=None if success else str(result.get("error") if isinstance(result, dict) else result),
    )


async def _store_fact_call(input: StoreFactInput, context: ToolContext, _on_progress) -> CallableToolResult[dict[str, Any]]:
    return await _wrap_memory_result("StoreFactTool", input, context)


async def _search_facts_call(input: SearchFactsInput, context: ToolContext, _on_progress) -> CallableToolResult[dict[str, Any]]:
    return await _wrap_memory_result("SearchFactsTool", input, context)


async def _retrieve_task_context_call(
    input: RetrieveTaskContextInput,
    context: ToolContext,
    _on_progress,
) -> CallableToolResult[dict[str, Any]]:
    payload = input
    if not payload.session_id and context.session_id:
        payload = input.model_copy(update={"session_id": context.session_id})
    return await _wrap_memory_result("RetrieveTaskContextTool", payload, context)


async def _recall_session_memory_call(
    input: RecallSessionMemoryInput,
    context: ToolContext,
    _on_progress,
) -> CallableToolResult[dict[str, Any]]:
    return await _wrap_memory_result("RecallSessionMemoryTool", input, context)


StoreFactCallable = build_callable_tool(
    name="store_fact",
    description="Persist a structured fact into the unified memory layer.",
    input_schema=StoreFactInput,
    call_fn=_store_fact_call,
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=False,
    interrupt_behavior="block",
)


SearchFactsCallable = build_callable_tool(
    name="search_facts",
    description="Search stored facts from the unified memory layer.",
    input_schema=SearchFactsInput,
    call_fn=_search_facts_call,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
    interrupt_behavior="cancel",
)


RetrieveTaskContextCallable = build_callable_tool(
    name="retrieve_task_context",
    description="Retrieve memory context relevant to a task or session query.",
    input_schema=RetrieveTaskContextInput,
    call_fn=_retrieve_task_context_call,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
    interrupt_behavior="cancel",
)


RecallSessionMemoryCallable = build_callable_tool(
    name="recall_session_memory",
    description="Recall prior session memory relevant to the current query.",
    input_schema=RecallSessionMemoryInput,
    call_fn=_recall_session_memory_call,
    is_read_only=True,
    is_concurrency_safe=True,
    is_destructive=False,
    interrupt_behavior="cancel",
)
