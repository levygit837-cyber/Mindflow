"""Storage layer (PostgreSQL + KuzuDB + Unified Architecture).

PostgreSQL for relational data, KuzuDB for vector embeddings and graph operations,
with unified interfaces and schemas integration.
"""

# Core Storage System
from .core import (
    CacheError,
    CacheInterface,
    ConnectionError,
    ConnectionPoolInterface,
    DatabaseError,
    DatabaseInterface,
    MigrationError,
    MigrationInterface,
    RepositoryInterface,
    StorageError,
    StorageInterface,
    VectorDatabaseInterface,
    VectorError,
)

# Storage-specific Interfaces
from .interfaces import (
    CacheManagerInterface,
    DatabaseRepositoryInterface,
    MemoryStoreInterface,
    VectorStoreInterface,
)

# PostgreSQL - Primary Storage
try:
    from .postgresql.connection import async_db_session, db_session
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    db_session = None
    async_db_session = None

try:
    from mindflow_backend.infra.database.connection import get_db_session as async_session_factory
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    async_session_factory = None

from .postgresql.models import (
    AgentMemoryCursor,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    ApiKey,
    Base,
    BrowserActionTrail,
    BrowserInstance,
    ChatMessage,
    ChatSession,
    ResearchFinding,
    ResearchSession,
    SessionReview,
    SessionReviewResult,
)

try:
    from .postgresql.repositories import (
        ChatRepository,
        NeuralRepository,
    )
except ModuleNotFoundError:  # pragma: no cover - optional in lightweight test envs
    ChatRepository = None
    NeuralRepository = None

# KuzuDB - Vector Storage
from .kuzudb.vector_store import KuzuDBVectorManager, KuzuDBVectorStore

# LangGraph - Checkpointing
from .langgraph.checkpointer import langgraph_checkpointer

# Storage Schemas
from .schemas import (
    CacheConfig,
    ConnectionConfig,
    DatabaseConfig,
    PoolConfig,
    StorageMemoryEntry,
    StorageMemoryStats,
    StorageMemoryWindow,
    VectorCollection,
    VectorConfig,
)

# Migration utilities
from .utils.migration_helpers import (
    backup_postgres_data,
    migrate_postgres_to_duckdb,
    restore_postgres_data,
    validate_migration_integrity,
)

__all__ = [
    # Core Storage System
    "StorageInterface",
    "DatabaseInterface",
    "VectorDatabaseInterface",
    "CacheInterface",
    "RepositoryInterface",
    "ConnectionPoolInterface",
    "MigrationInterface",
    # Exceptions
    "StorageError",
    "DatabaseError",
    "VectorError",
    "CacheError",
    "ConnectionError",
    "MigrationError",
    # Storage-specific Interfaces
    "DatabaseRepositoryInterface",
    "VectorStoreInterface",
    "CacheManagerInterface",
    "MemoryStoreInterface",
    # PostgreSQL - Primary Storage
    "Base",
    "db_session",
    "async_db_session",
    "async_session_factory",
    # Models
    "ChatSession",
    "ChatMessage",
    "AgentMemoryEvent",
    "AgentMemoryCursor",
    "AgentMemoryWindow",
    "AgentMemoryFact",
    "ResearchSession",
    "SessionReview",
    "SessionReviewResult",
    "BrowserActionTrail",
    "ResearchFinding",
    "BrowserInstance",
    "ApiKey",
    # Repositories
    "ChatRepository",
    "NeuralRepository",
    # KuzuDB - Vector Storage
    "KuzuDBVectorStore",
    "KuzuDBVectorManager",
    # LangGraph
    "langgraph_checkpointer",
    # Storage Schemas
    "DatabaseConfig",
    "ConnectionConfig",
    "PoolConfig",
    "VectorConfig",
    "VectorCollection",
    "CacheConfig",
    "StorageMemoryEntry",
    "StorageMemoryWindow",
    "StorageMemoryStats",
    # Migration utilities
    "backup_postgres_data",
    "migrate_postgres_to_duckdb",
    "restore_postgres_data",
    "validate_migration_integrity",
]
