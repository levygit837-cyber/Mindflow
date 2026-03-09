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

from .embeddings import EmbeddingProvider, VectorStore, cosine_similarity
from .storage import MemoryDatabase, MemoryVectorDB
from .retrieval import SemanticRetriever, ContextRetriever, ResultRanker
from .core import MemoryServiceInterface, MemoryRetrievalResult

__all__ = [
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
    
    # Core
    "MemoryServiceInterface",
    "MemoryRetrievalResult",
]
