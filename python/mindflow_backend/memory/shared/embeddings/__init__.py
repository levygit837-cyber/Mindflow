"""Shared Embeddings System.

Provides the unified EmbeddingProviderFactory and the IEmbeddingProvider protocol.
Use get_embedding_provider() to get a singleton configured from settings.
"""

from .factory import (
    EmbeddingBackend,
    EmbeddingProviderFactory,
    GeminiProvider,
    HashFallbackProvider,
    IEmbeddingProvider,
    OllamaProvider,
    OpenAIProvider,
    SentenceTransformerProvider,
    TFIDFProvider,
    get_embedding_provider,
)

__all__ = [
    "EmbeddingBackend",
    "EmbeddingProviderFactory",
    "GeminiProvider",
    "HashFallbackProvider",
    "IEmbeddingProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "SentenceTransformerProvider",
    "TFIDFProvider",
    "get_embedding_provider",
]
