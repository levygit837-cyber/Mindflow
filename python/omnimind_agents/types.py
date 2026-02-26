from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

LLMProvider = Literal["anthropic", "openai", "ollama", "google", "vertexai"]
OutputCategory = Literal["explanation", "decision", "code_result", "summary", "response"]
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


class NodeCategory(str, Enum):
    LLM_INVOKE = "LLM_INVOKE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    SUBGRAPH = "SUBGRAPH"
    INTERNAL = "INTERNAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class StreamEvent:
    id: str
    seq: int
    type: StreamEventType
    mode: StreamModeName
    data: str
    meta: Dict[str, Any] = field(default_factory=dict)


MetaDict = Dict[str, Any]
AnyRecord = Dict[str, Any]
AnyList = List[Any]
