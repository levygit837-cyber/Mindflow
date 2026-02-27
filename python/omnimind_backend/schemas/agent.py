from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from omnimind_backend.schemas.common import LLMProvider

TopicType = Literal["project_main", "project_topic", "standalone"]
MindJobStatus = Literal["queued", "running", "completed", "failed"]


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=100000)
    provider: LLMProvider | None = None
    model: str | None = None
    sessionId: str | None = None
    # Backward compatibility with old web contract.
    conversationId: str | None = None
    debugSteps: bool = False


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    topic_about: str | None = Field(default=None, max_length=2000)
    topic_type: TopicType = "standalone"
    folder_path: str | None = None
    project_root_session_id: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    topic_about: str | None = Field(default=None, max_length=2000)


class SessionOut(BaseModel):
    id: str
    title: str
    topic_about: str | None = None
    topic_type: TopicType
    folder_path: str | None = None
    project_root_session_id: str | None = None
    createdAt: str
    updatedAt: str


class MessageOut(BaseModel):
    id: str
    sessionId: str
    role: Literal["user", "assistant"] | str
    content: str
    thoughts: str | None = None
    toolCalls: list[dict[str, Any]] | None = None
    runId: str | None = None
    createdAt: str


class SessionRunOut(BaseModel):
    id: str
    sessionId: str
    runId: str
    label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: str


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
    sessionId: str
    wallTime: str


class AgentChatStreamPayload(BaseModel):
    """Internal normalized stream payload from runtime."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event: StreamEvent
    assistant_text_delta: str = ""
    assistant_thought_delta: str = ""
    tool_call: dict[str, Any] | None = None


class ProjectCreate(BaseModel):
    folderPath: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    topicAbout: str | None = Field(default=None, max_length=2000)


class ProjectOut(BaseModel):
    folderPath: str
    projectSessionId: str | None = None
    title: str
    hasSessions: bool
    sessionsCount: int
    updatedAt: str | None = None


class MindSessionLinkCreate(BaseModel):
    folderPath: str = Field(min_length=1)
    sourceSessionId: str
    targetSessionId: str
    label: str | None = Field(default=None, max_length=200)


class MindSessionLinkOut(BaseModel):
    id: int
    folderPath: str
    sourceSessionId: str
    targetSessionId: str
    label: str | None = None
    createdAt: str


class MindJobCreate(BaseModel):
    folderPath: str = Field(min_length=1)
    sessionIds: list[str] = Field(min_length=1)
    query: str | None = Field(default=None, max_length=20000)
    sourceSessionId: str | None = None


class MindJobOut(BaseModel):
    id: str
    folderPath: str
    sessionIds: list[str]
    query: str | None = None
    status: MindJobStatus
    resultSummary: str | None = None
    errorMessage: str | None = None
    createdAt: str
    startedAt: str | None = None
    completedAt: str | None = None


class MindSandboxQueryRequest(BaseModel):
    folderPath: str | None = None
    sessionIds: list[str] = Field(min_length=1)
    query: str | None = Field(default=None, max_length=20000)
    tools: list[str] = Field(default_factory=list)
    selectedSnippets: list[str] = Field(default_factory=list)


class MindSandboxQueryResponse(BaseModel):
    output: str
    usedTools: list[str]
    sessionIds: list[str]
    runId: str
    neuralFilePath: str | None = None


class AllowlistPathOut(BaseModel):
    path: str
