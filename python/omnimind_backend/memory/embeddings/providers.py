"""Embedding generation providers."""

import hashlib
import math
import os
import re
from typing import List

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def _tokenize(text: str) -> List[str]:
    """Tokenize text for hash-based embeddings."""
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


class EmbeddingProvider:
    """Provider for generating text embeddings."""
    
    def __init__(self, embedding_dims: int = 768):
        self.embedding_dims = embedding_dims
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self._embed_text_llm(text, self.embedding_dims)
    
    def _embed_text_llm(self, text: str, dims: int) -> List[float]:
        """Generate real semantic embeddings using configured LLM provider.

        Falls back to hash-based embeddings if the embedding model is unavailable.
        """
        settings = get_settings()
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            api_key = settings.google_api_key
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

            if api_key:
                embeddings_model = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=api_key,
                )
                vector = embeddings_model.embed_query(text)
                # Truncate or pad to match expected dims
                if len(vector) > dims:
                    vector = vector[:dims]
                elif len(vector) < dims:
                    vector.extend([0.0] * (dims - len(vector)))
                return vector
        except Exception as exc:
            _logger.warning("embedding_llm_failed_falling_back_to_hash", error=str(exc))

        return self._embed_text_hash_fallback(text, dims)
    
    def _embed_text_hash_fallback(self, text: str, dims: int) -> List[float]:
        """Hash-based fallback embedding (low quality, for offline/testing only)."""
        vector = [0.0] * dims
        tokens = _tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = digest % dims
            sign = -1.0 if ((digest >> 1) & 1) else 1.0
            vector[idx] += sign

        norm = math.sqrt(sum(v * v for v in vector))
        if norm <= 0:
            return vector
        return [v / norm for v in vector]
