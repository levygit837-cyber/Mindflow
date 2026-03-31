"""Embedding generation and vector operations."""

from .providers import EmbeddingProvider
from .similarity import cosine_similarity
from .vector_store import VectorStore

__all__ = [
    "EmbeddingProvider",
    "VectorStore", 
    "cosine_similarity"
]
