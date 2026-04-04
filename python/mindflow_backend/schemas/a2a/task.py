from typing import Literal, Union, Any
from pydantic import BaseModel

class TaskStatusUpdateEvent(BaseModel):
    """Event triggered when a A2A Task changes status."""
    type: Literal["TaskStatusUpdateEvent"] = "TaskStatusUpdateEvent"
    status: str
    message: str | None = None
    error: str | None = None

class BaseArtifactPart(BaseModel):
    pass

class TextPart(BaseArtifactPart):
    """Artifact Part payload for text based interactions."""
    type: Literal["text"] = "text"
    text: str

class DataPart(BaseArtifactPart):
    """Artifact Part payload for structured data JSON outputs."""
    type: Literal["data"] = "data"
    data: dict[str, Any]

class FilePart(BaseArtifactPart):
    """Artifact Part payload for generating files."""
    type: Literal["file"] = "file"
    content: str
    filename: str | None = None
    mime_type: str | None = None

A2AItemPart = Union[TextPart, DataPart, FilePart]

class A2AMessage(BaseModel):
    """Input message for the Agent-to-Agent Gateway Task schema."""
    role: Literal["user", "agent"]
    parts: list[A2AItemPart]
    target_agent: str | None = None
    context_id: str | None = None

class A2AArtifact(BaseModel):
    """An artifact returned by an A2A execution containing parts."""
    parts: list[A2AItemPart]

class TaskArtifactUpdateEvent(BaseModel):
    """Event triggered to steam out an artifact chunk."""
    type: Literal["TaskArtifactUpdateEvent"] = "TaskArtifactUpdateEvent"
    artifact: A2AArtifact
    append: bool = True
