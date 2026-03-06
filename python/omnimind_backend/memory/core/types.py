"""Memory service types and dataclasses."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class MemoryRetrievalResult:
    """Result of memory retrieval operation."""
    context: str
    references: List[str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass(slots=True)
class MemoryEvent:
    """Memory event data."""
    id: int
    session_id: str
    agent_id: str
    role: str
    content: str
    token_count: int
    source_message_id: Optional[int] = None
    created_at: Optional[str] = None


@dataclass(slots=True)
class MemoryWindow:
    """Memory window data."""
    id: int
    session_id: str
    agent_id: str
    window_start: int
    window_end: int
    summary: str
    event_count: int
    created_at: Optional[str] = None


@dataclass(slots=True)
class MemoryCursor:
    """Memory cursor data."""
    session_id: str
    agent_id: str
    token_total: int
    tokens_since_summary: int
    window_index: int
    last_summary_at: Optional[str] = None
