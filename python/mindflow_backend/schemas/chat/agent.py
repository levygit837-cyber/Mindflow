from pathlib import Path
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from mindflow_backend.infra.sanitizer import sanitize_message
from mindflow_backend.schemas.api.common import BaseResponse
from mindflow_backend.schemas.core.common import LLMProvider


class AgentChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(min_length=1, max_length=100000)
    provider: LLMProvider | None = None
    model: str | None = None
    sessionId: str | None = Field(default=None, alias="session_id")
    debugSteps: bool = False
    orchestrate: bool = False
    agent_type: str | None = Field(
        default=None,
        validation_alias=AliasChoices("agent_type", "agent"),
        serialization_alias="agent_type",
    )
    folder_path: str | None = Field(
        default=None,
        description="Working directory for filesystem tools (root_dir for sandboxed operations)",
    )

    @field_validator("folder_path", mode="before")
    @classmethod
    def normalize_folder_path(cls, value: Any) -> Any:
        if value is None or not isinstance(value, str):
            return value

        candidate = value.strip()
        if not candidate:
            return None

        try:
            path = Path(candidate).expanduser()
            if path.exists():
                if path.is_file():
                    return str(path.resolve().parent)
                if path.is_dir():
                    return str(path.resolve())
        except OSError:
            return candidate

        return candidate

    @field_validator("message")
    @classmethod
    def sanitize_input_message(cls, value: str) -> str:
        return sanitize_message(value)


class AgentExecutionResponse(BaseResponse):
    """Response for execution status and control actions."""

    execution_id: str = Field(description="Execution ID")
    status: str = Field(description="Execution status")
    action: str | None = Field(default=None, description="Requested control action")
    paused: bool = Field(default=False, description="Whether the execution is paused")
    can_resume: bool = Field(default=False, description="Whether the execution can be resumed")
    progress: float | None = Field(default=None, description="Execution progress percentage")
    snapshot: dict[str, Any] = Field(default_factory=dict, description="Execution snapshot or state details")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional execution metadata")


class ChatMessageSchema(BaseModel):
    id: int | None = None
    role: str
    content: str
    provider: str | None = None
    model: str | None = None
    created_at: str | None = None


class ChatSessionSchema(BaseModel):
    id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    messages: list[ChatMessageSchema] | None = None


StreamModeName = Literal["updates", "messages", "custom", "values", "debug"]

# Rich event types for orchestrator UI (OrchestratorStreamRenderer).
# Notifier: generic channel for any info to show in UI (kind, message, details).
StreamEventType = Literal[
    "thought",
    "tool_call",
    "tool_result",
    "response",
    "step",
    "agent_step",
    "done",
    "error",
    "notifier",
    # Orchestrator flow
    "orchestrator_thinking_start",
    "orchestrator_thinking",
    "orchestrator_thinking_end",
    "reflection_mode_start",
    "reflection_mode_end",
    "orchestrator_decision",
    "agent_delegation_start",
    "agent_delegation_complete",
    "specialist_activation",
    "specialist_thinking",
    "orchestrator_step",
    "tool_operation_start",
    "tool_operation_update",
    "tool_operation_complete",
    "routing_analysis",
    "agent_execution_start",
]


class NotifierPayload(BaseModel):
    """Flexible payload for 'notifier' events. Any action or info to show in the UI.

    Use kind (or category) to identify the type; message for display; details for extra data.
    Example kinds: file_read, file_write, tool_start, tool_end, context_loaded, search_done, info, warning.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    kind: str = Field(
        ...,
        alias="category",
        description="Notification type: file_read, file_write, tool_start, context_loaded, info, etc.",
    )
    message: str = Field(..., description="Short text to display in the UI")
    details: dict[str, Any] = Field(default_factory=dict, description="Optional extra data (file_path, start_line, tool_name, etc.)")


class StreamEventMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    runId: str | None = None
    parentRunId: str | None = None
    node: str | None = None
    nodeLabel: str | None = None
    nodeCategory: str | None = None
    userVisible: bool | None = None
    toolCallId: str | None = None
    provider: LLMProvider | None = None
    model: str | None = None
    status: Literal["start", "update", "end"] | None = None
    path: list[str] | None = None
    turnRunId: str | None = None
    insertBefore: str | None = None
    firstResponseMarker: str | None = None
    category: str | None = None  # open-ended: "text", "explanation", "decision", "code_result", "summary", "response", etc.
    agent: str | None = None  # Current agent (orchestrator, coder, analyst, researcher) for UI


class StreamEvent(BaseModel):
    id: str
    seq: int
    type: StreamEventType
    mode: StreamModeName
    data: str
    meta: StreamEventMeta | None = None


class LogEntry(StreamEvent):
    turnId: str
    wallTime: str


class AgentChatStreamPayload(BaseModel):
    """Internal normalized stream payload from runtime."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event: StreamEvent
    assistant_text_delta: str = ""
    assistant_thought_delta: str = ""
    tool_call: dict[str, Any] | None = None
