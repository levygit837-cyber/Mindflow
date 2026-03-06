"""Context services for OmniMind backend.

This module provides services for semantic context retrieval,
embedding generation, and vector database management.
"""

from __future__ import annotations

# Factory functions for context services
def get_retrieval_service():
    """Factory function for RetrievalService."""
    from omnimind_backend.services.context.retrieval_service import RetrievalService
    return RetrievalService()

def get_embedding_service():
    """Factory function for EmbeddingService."""
    from omnimind_backend.services.context.embedding_service import EmbeddingService
    return EmbeddingService()

def get_vector_service():
    """Factory function for VectorService."""
    from omnimind_backend.services.context.vector_service import VectorService
    return VectorService()

# Public exports
__all__ = [
    "get_retrieval_service",
    "get_embedding_service", 
    "get_vector_service",
]
