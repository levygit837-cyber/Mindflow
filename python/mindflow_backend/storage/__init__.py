"""Storage layer (PostgreSQL + KuzuDB + Unified Architecture).

PostgreSQL for relational data, KuzuDB for vector embeddings and graph operations,
with unified interfaces and schemas integration.
"""

# Core Storage System
from .core import (
    StorageInterface,
    DatabaseInterface,
    VectorDatabaseInterface,
    CacheInterface,
    RepositoryInterface,
    ConnectionPoolInterface,
    MigrationInterface,
    StorageError,
    DatabaseError,
    VectorError,
    CacheError,
    ConnectionError,
    MigrationError,
)

# Storage-specific Interfaces
from .interfaces import (
    DatabaseRepositoryInterface,
    VectorStoreInterface,
    CacheManagerInterface,
    MemoryStoreInterface,
)

# PostgreSQL - Primary Storage
from .postgresql.connection import db_session, async_db_session
from .postgresql.models import (
    Base,
    AgentMemoryCursor,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    ChatMessage,
    ChatSession,
    BrowserActionTrail,
    BrowserInstance,
    ResearchFinding,
    ResearchSession,
)
from .postgresql.repositories import (
    ChatRepository,
    NeuralRepository,
)

# KuzuDB - Vector Storage
from .kuzudb.vector_store import KuzuDBVectorStore, KuzuDBVectorManager

# LangGraph - Checkpointing
from .langgraph.checkpointer import langgraph_checkpointer

# Storage Schemas
from .schemas import (
    DatabaseConfig,
    ConnectionConfig,
    PoolConfig,
    VectorConfig,
    VectorCollection,
    CacheConfig,
    StorageMemoryEntry,
    StorageMemoryWindow,
    StorageMemoryStats,
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
    # Models
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
