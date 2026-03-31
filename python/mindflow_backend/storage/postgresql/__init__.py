"""PostgreSQL storage layer.

Primary relational database for MindFlow backend.
"""

try:
    from .connection import db_session
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    db_session = None
from .models import (
    AgentMemoryCursor,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    BrowserActionTrail,
    BrowserInstance,
    ChatMessage,
    ChatSession,
    ResearchFinding,
    ResearchSession,
)

try:
    from .repositories import (
        ChatRepository,
        NeuralRepository,
    )
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    ChatRepository = None
    NeuralRepository = None

__all__ = [
    "db_session",
    "ChatSession",
    "ChatMessage",
    "AgentMemoryEvent",
    "AgentMemoryCursor",
    "AgentMemoryWindow",
    "AgentMemoryFact",
    "ResearchSession",
    "BrowserActionTrail",
    "ResearchFinding",
    "BrowserInstance",
    "ChatRepository",
    "NeuralRepository",
]
