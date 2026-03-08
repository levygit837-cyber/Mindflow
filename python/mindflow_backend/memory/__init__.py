"""Agent memory services for long-context compression and retrieval."""

# Core services
from .core.service import MemoryService
from .core.agent_memory_service import AgentMemoryService, get_memory_service
from .core.types import MemoryRetrievalResult
from .core.interfaces import MemoryServiceInterface

# Embeddings
from .embeddings.providers import EmbeddingProvider
from .embeddings.vector_store import VectorStore
from .embeddings.similarity import cosine_similarity

# Storage
from .storage.database import MemoryDatabase
from .storage.vector_db import MemoryVectorDB

# Retrieval
from .retrieval.semantic import SemanticRetriever
from .retrieval.context import ContextRetriever
from .retrieval.ranking import ResultRanker

# API
from .api.controller import MemoryController
from .api.routes import router

# Utils
from mindflow_backend.utils.core import estimate_token_count

# Legacy exports for backward compatibility
__all__ = [
    # Core
    "MemoryService",
    "AgentMemoryService", 
    "MemoryRetrievalResult",
    "get_memory_service",
    "MemoryServiceInterface",
    
    # Embeddings
    "EmbeddingProvider",
    "VectorStore",
    "cosine_similarity",
    
    # Storage
    "MemoryDatabase",
    "MemoryVectorDB",
    
    # Retrieval
    "SemanticRetriever",
    "ContextRetriever", 
    "ResultRanker",
    
    # API
    "MemoryController",
    "router",
    
    # Utils
    "estimate_token_count",
]
