"""Embedding generation and vector operations."""

from .providers import EmbeddingProvider
from .vector_store import VectorStore
from .similarity import cosine_similarity

__all__ = [
    "EmbeddingProvider",
    "VectorStore", 
    "cosine_similarity"
]
