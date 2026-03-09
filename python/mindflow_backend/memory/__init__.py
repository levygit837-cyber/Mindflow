"""Agent memory services for long-context compression and retrieval."""

# Session Memory - Memória Semântica de Sessões
from .session_memory import (
    SessionMemoryService,
    SessionStorage,
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
    LangGraphCheckpointer,
    RollingWindows,
    FactExtractor,
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

# API
from .api.controller import MemoryController
from .api.routes import router

# Utils
from mindflow_backend.utils.core import estimate_token_count

__all__ = [
    # Session Memory
    "SessionMemoryService",
    "SessionStorage",

    # Task Memory
    "TaskMemoryService",
    "TaskRetriever",
    "TaskDecomposer",
    "TaskIntegration",

    # Agent Memory
    "AgentMemoryService",
    "LangGraphCheckpointer",
    "RollingWindows",
    "FactExtractor",

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

    # API
    "MemoryController",
    "router",

    # Utils
    "estimate_token_count",
]
