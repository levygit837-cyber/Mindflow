"""Callable orchestration tools backed by the legacy runtime implementations."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindflow_backend.agents.tools.orchestration.agent_tool import AgentTool
from mindflow_backend.communication.tools.send_message import SendMessageTool
from mindflow_backend.schemas.tools import CallableToolResult, ToolContext, build_callable_tool


class AgentToolInput(BaseModel):
    description: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    subagent_type: str = "analyst"
    model: str | None = None
    run_in_background: bool | None = None
    name: str | None = None
    isolation: str | None = None
    scope: list[str] = Field(default_factory=list)
    context: str = ""
    expected_output: str = ""


class SendMessageInput(BaseModel):
    to: str = Field(min_length=1)
    summary: str | None = None
    message: str = Field(min_length=1)


def _configure_legacy_tool(tool: Any, context: ToolContext) -> Any:
    if context.root_dir and hasattr(tool, "root_dir"):
        tool.root_dir = context.root_dir
    if context.session_id and hasattr(tool, "session_id"):
        tool.session_id = context.session_id
    if context.execution_id and hasattr(tool, "execution_id"):
        tool.execution_id = context.execution_id
    agent_id = (context.metadata or {}).get("agent_id")
    if agent_id and hasattr(tool, "agent_id"):
        tool.agent_id = agent_id
    return tool


async def _agent_tool_call(
    input: AgentToolInput,
    context: ToolContext,
    _on_progress,
) -> CallableToolResult[dict[str, Any]]:
    tool = _configure_legacy_tool(AgentTool(), context)
    result = await tool.execute(**input.model_dump())
    success = not str(result).lower().startswith(("error:", "delegation failed"))
    return CallableToolResult(
        success=success,
        data={"output": result},
        error=None if success else str(result),
    )


async def _send_message_call(
    input: SendMessageInput,
    context: ToolContext,
    _on_progress,
) -> CallableToolResult[dict[str, Any]]:
    tool = _configure_legacy_tool(SendMessageTool(), context)
    result = await tool.execute(**input.model_dump())
    success = not str(result).lower().startswith(("error:", "failed"))
    return CallableToolResult(
        success=success,
        data={"output": result},
        error=None if success else str(result),
    )


AgentToolCallable = build_callable_tool(
    name="AgentTool",
    description=AgentTool().description,
    input_schema=AgentToolInput,
    call_fn=_agent_tool_call,
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=False,
    interrupt_behavior="block",
)


SendMessageCallable = build_callable_tool(
    name="SendMessage",
    description=SendMessageTool().description,
    input_schema=SendMessageInput,
    call_fn=_send_message_call,
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=False,
    interrupt_behavior="block",
)
