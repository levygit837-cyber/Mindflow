"""Storage layer (PostgreSQL + KuzuDB).

PostgreSQL for relational data, KuzuDB for vector embeddings and graph operations.
"""

# PostgreSQL - Primary Storage
from .postgresql.connection import db_session
from .postgresql.models import (
    AgentMemoryCursor,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    ChatMessage,
    ChatSession,
    BrowserInstance,
    ResearchAction,
    ResearchFinding,
    ResearchSession,
)
from .postgresql.repositories import (
    AgentMemoryCursorRepository,
    AgentMemoryEventRepository,
    AgentMemoryFactRepository,
    AgentMemoryWindowRepository,
    ChatMessageRepository,
    ChatSessionRepository,
    ResearchSessionRepository,
)

# KuzuDB - Vector Storage
from .kuzudb.vector_store import KuzuDBVectorStore, KuzuDBVectorManager

# LangGraph - Checkpointing
from .langgraph.checkpointer import langgraph_checkpointer

# Migration utilities
from .utils.migration_helpers import (
    backup_postgres_data,
    migrate_postgres_to_duckdb,
    restore_postgres_data,
    validate_migration_integrity,
)

__all__ = [
    # PostgreSQL - Primary Storage
    "db_session",
    # Models
    "ChatSession",
    "ChatMessage",
    "AgentMemoryEvent",
    "AgentMemoryCursor",
    "AgentMemoryWindow",
    "AgentMemoryFact",
    "ResearchSession",
    "ResearchAction",
    "ResearchFinding",
    "BrowserInstance",
    # Repositories
    "ChatSessionRepository",
    "ChatMessageRepository",
    "AgentMemoryEventRepository",
    "AgentMemoryCursorRepository",
    "AgentMemoryWindowRepository",
    "AgentMemoryFactRepository",
    "ResearchSessionRepository",
    # KuzuDB - Vector Storage
    "KuzuDBVectorStore",
    "KuzuDBVectorManager",
    # LangGraph
    "langgraph_checkpointer",
    # Migration utilities
    "backup_postgres_data",
    "migrate_postgres_to_duckdb",
    "restore_postgres_data",
    "validate_migration_integrity",
]
