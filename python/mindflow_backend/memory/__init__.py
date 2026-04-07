"""Agent memory services for long-context compression and retrieval."""

# Session Memory - Memória Semântica de Sessões
# Utils
from mindflow_backend.utils.core import estimate_token_count

# Agent Memory - Memória Agêntica (LangGraph)
from .agent_memory import (
    AgentMemoryService,
    RollingWindow,
    langgraph_checkpointer,
)

# Agentic store (LangGraph Store)
from .agent_memory.store import AgenticMemoryStore
from .session_memory import (
    MemoryDatabase,
    SessionMemoryService,
)

# Intelligent Memory System (NEW)
from .category_manager import CategoryManager, MemoryScope, MemoryType
from .graph_hooks import MemoryHooks
from .memory_service import MemoryService, SearchMode
from .observers import (
    DynamicCodeParser,
    EventBusMemoryObserver,
    MemoryObserverCoordinator,
    ObserverConfig,
    PostToolUseObserver,
)

# Shared Components - Componentes Compartilhados
from .shared import (
    ContextRetriever,
    MemoryRetrievalResult,
    MemoryServiceInterface,
    ResultRanker,
    SemanticRetriever,
)

# Embedding factory
from .shared.embeddings.factory import EmbeddingBackend, IEmbeddingProvider, get_embedding_provider

# Task Memory - Memória Semântica de Tasks
from .task_memory import (
    TaskDecomposer,
    TaskIntegration,
    TaskMemoryService,
    TaskRetriever,
)

# Cross-task API
from .task_memory.api import CrossTaskContextAPI, get_cross_task_api

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

    # Intelligent Memory System (NEW)
    "CategoryManager",
    "MemoryService",
    "MemoryScope",
    "MemoryType",
    "SearchMode",
    "MemoryHooks",
    "EventBusMemoryObserver",
    "PostToolUseObserver",
    "DynamicCodeParser",
    "MemoryObserverCoordinator",
    "ObserverConfig",
]
