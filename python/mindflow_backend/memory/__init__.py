"""Agent memory services for long-context compression and retrieval."""

# Session Memory - Memória Semântica de Sessões
from .session_memory import (
    SessionMemoryService,
    MemoryDatabase,
)

# Task Memory - Memória Semântica de Tasks
from .task_memory import (
    TaskMemoryService,
    TaskRetriever,
    TaskDecomposer,
    TaskIntegration,
)

# Agent Memory - Memória Agêntica (LangGraph)
from .agent_memory import (
    AgentMemoryService,
    langgraph_checkpointer,
    RollingWindow,
)

# Shared Components - Componentes Compartilhados
from .shared import (
    SemanticRetriever,
    ContextRetriever,
    ResultRanker,
    MemoryServiceInterface,
    MemoryRetrievalResult,
)

# Embedding factory
from .shared.embeddings.factory import get_embedding_provider, IEmbeddingProvider, EmbeddingBackend

# Agentic store (LangGraph Store)
from .agent_memory.store import AgenticMemoryStore

# Cross-task API
from .task_memory.api import CrossTaskContextAPI, get_cross_task_api

# Utils
from mindflow_backend.utils.core import estimate_token_count

_memory_facade = None


def get_memory_service():
    """Return the canonical MemoryFacade instance.

    The facade exposes the three public methods defined in Phase 1:
        record_message, recall, get_agent_snapshot.
    """
    global _memory_facade
    from .facade import MemoryFacade

    if _memory_facade is None:
        _memory_facade = MemoryFacade()
    return _memory_facade

__all__ = [
    # Session Memory
    "SessionMemoryService",
    "MemoryDatabase",

    # Task Memory
    "TaskMemoryService",
    "TaskRetriever",
    "TaskDecomposer",
    "TaskIntegration",

    # Agent Memory
    "AgentMemoryService",
    "langgraph_checkpointer",
    "RollingWindow",

    # Shared Components
    "SemanticRetriever",
    "ContextRetriever",
    "ResultRanker",
    "MemoryServiceInterface",
    "MemoryRetrievalResult",

    # Embedding factory
    "get_embedding_provider",
    "IEmbeddingProvider",
    "EmbeddingBackend",

    # Agentic store
    "AgenticMemoryStore",

    # Cross-task API
    "CrossTaskContextAPI",
    "get_cross_task_api",

    # Utils
    "estimate_token_count",
    "get_memory_service",

    # Canonical facade (Phase 1)
    "MemoryFacade",
]
