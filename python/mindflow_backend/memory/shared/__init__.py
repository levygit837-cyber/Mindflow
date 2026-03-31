"""Shared Components - Componentes Compartilhados.

Componentes reutilizáveis entre os 3 tipos de memória:
- Sistema unificado de embeddings
- Camada de abstração de storage
- Algoritmos genéricos de recuperação
- Interfaces base e tipos compartilhados

Submodules:
- embeddings: Sistema de geração e gerenciamento de embeddings
- storage: Camada de abstração de banco de dados
- retrieval: Algoritmos de busca semântica e por similaridade
- core: Interfaces base, tipos e exceções compartilhadas
"""

from .core import MemoryRetrievalResult, MemoryServiceInterface
from .embeddings import IEmbeddingProvider
from .retrieval import ContextRetriever, ResultRanker, SemanticRetriever
from .storage import MemoryDatabase, MemoryVectorDB, VectorStore

__all__ = [
    # Embeddings
    "IEmbeddingProvider",
    "VectorStore",
    
    # Storage
    "MemoryDatabase",
    "MemoryVectorDB",
    
    # Retrieval
    "SemanticRetriever",
    "ContextRetriever", 
    "ResultRanker",
    
    # Core
    "MemoryServiceInterface",
    "MemoryRetrievalResult",
]
