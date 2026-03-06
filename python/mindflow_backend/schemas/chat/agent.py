from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

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
]


class StreamEventMeta(BaseModel):
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
    category: Literal["explanation", "decision", "code_result", "summary", "response"] | None = None


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
