"""Unified embedding provider factory for MindFlow memory system.

Supports local NLP models (sentence-transformers, TF-IDF, hybrid),
cloud providers (Gemini, OpenAI), local model servers (Ollama),
and a hash-based fallback for offline/testing.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import os
import re
from enum import Enum
from functools import lru_cache
from typing import Protocol, runtime_checkable

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class EmbeddingBackend(str, Enum):
    SENTENCE_TRANSFORMER = "sentence_transformer"
    TFIDF = "tfidf"
    HYBRID = "hybrid"
    GEMINI = "gemini"
    OPENAI = "openai"
    OLLAMA = "ollama"
    HASH_FALLBACK = "hash_fallback"


@runtime_checkable
class IEmbeddingProvider(Protocol):
    """Unified contract for all embedding providers."""

    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def dimension(self) -> int: ...
    def backend(self) -> EmbeddingBackend: ...


# ---------------------------------------------------------------------------
# Hash fallback (offline / testing)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _hash_embed(text: str, dims: int) -> list[float]:
    vector = [0.0] * dims
    tokens = _tokenize(text)
    if not tokens:
        return vector
    for token in tokens:
        digest = int(hashlib.sha256(token.encode()).hexdigest(), 16)
        idx = digest % dims
        sign = -1.0 if ((digest >> 1) & 1) else 1.0
        vector[idx] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


class HashFallbackProvider:
    def __init__(self, dims: int = 768) -> None:
        self._dims = dims

    async def embed(self, text: str) -> list[float]:
        return _hash_embed(text, self._dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embed(t, self._dims) for t in texts]

    def dimension(self) -> int:
        return self._dims

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.HASH_FALLBACK


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class GeminiProvider:
    def __init__(self, *, model_name: str = "models/text-embedding-004", dims: int = 768, api_key: str | None = None) -> None:
        self._model_name = model_name
        self._dims = dims
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self._model = None

    def _get_model(self):
        if self._model is None:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            self._model = GoogleGenerativeAIEmbeddings(
                model=self._model_name,
                google_api_key=self._api_key,
            )
        return self._model

    def _normalize(self, vector: list[float]) -> list[float]:
        if len(vector) > self._dims:
            return vector[: self._dims]
        if len(vector) < self._dims:
            vector = vector + [0.0] * (self._dims - len(vector))
        return vector

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vector = await loop.run_in_executor(None, model.embed_query, text)
        return self._normalize(vector)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vectors = await loop.run_in_executor(None, model.embed_documents, texts)
        return [self._normalize(v) for v in vectors]

    def dimension(self) -> int:
        return self._dims

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.GEMINI


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider:
    def __init__(self, *, model_name: str = "text-embedding-3-small", dims: int = 1536, api_key: str | None = None) -> None:
        self._model_name = model_name
        self._dims = dims
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = None

    def _get_model(self):
        if self._model is None:
            from langchain_openai import OpenAIEmbeddings
            self._model = OpenAIEmbeddings(model=self._model_name, openai_api_key=self._api_key)
        return self._model

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vector = await loop.run_in_executor(None, model.embed_query, text)
        return vector[: self._dims]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vectors = await loop.run_in_executor(None, model.embed_documents, texts)
        return [v[: self._dims] for v in vectors]

    def dimension(self) -> int:
        return self._dims

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.OPENAI


# ---------------------------------------------------------------------------
# Ollama provider
# ---------------------------------------------------------------------------

class OllamaProvider:
    def __init__(self, *, model_name: str = "nomic-embed-text", dims: int = 768, base_url: str | None = None) -> None:
        self._model_name = model_name
        self._dims = dims
        self._base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._model = None

    def _get_model(self):
        if self._model is None:
            from langchain_ollama import OllamaEmbeddings
            self._model = OllamaEmbeddings(model=self._model_name, base_url=self._base_url)
        return self._model

    async def embed(self, text: str) -> list[float]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vector = await loop.run_in_executor(None, model.embed_query, text)
        return vector[: self._dims]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_event_loop()
        model = self._get_model()
        vectors = await loop.run_in_executor(None, model.embed_documents, texts)
        return [v[: self._dims] for v in vectors]

    def dimension(self) -> int:
        return self._dims

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.OLLAMA


# ---------------------------------------------------------------------------
# SentenceTransformer provider (wraps NLPEmbeddingService)
# ---------------------------------------------------------------------------

class SentenceTransformerProvider:
    def __init__(self, *, model_name: str = "all-MiniLM-L6-v2", dims: int | None = None) -> None:
        self._model_name = model_name
        self._dims = dims  # None = use model's native dim
        self._service = None

    async def _get_service(self):
        if self._service is None:
            from mindflow_backend.services.nlp_embeddings.nlp_embedding_service import (
                NLPEmbeddingService, EmbeddingConfig, EmbeddingMethod,
            )
            config = EmbeddingConfig(method=EmbeddingMethod.SENTENCE_TRANSFORMER, model_name=self._model_name)
            self._service = NLPEmbeddingService(config)
            await self._service.fit([])  # loads model
        return self._service

    async def embed(self, text: str) -> list[float]:
        svc = await self._get_service()
        result = await svc.generate_embeddings([text])
        vec = result[0]
        return vec[: self._dims] if self._dims else vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        svc = await self._get_service()
        results = await svc.generate_embeddings(texts)
        return [v[: self._dims] if self._dims else v for v in results]

    def dimension(self) -> int:
        if self._dims:
            return self._dims
        # all-MiniLM-L6-v2 = 384, all-mpnet-base-v2 = 768
        return 384

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.SENTENCE_TRANSFORMER


# ---------------------------------------------------------------------------
# TF-IDF provider (wraps NLPEmbeddingService) — requires fit() corpus
# ---------------------------------------------------------------------------

class TFIDFProvider:
    def __init__(self, *, dims: int = 768, corpus: list[str] | None = None) -> None:
        self._dims = dims
        self._corpus = corpus or ["placeholder"]
        self._service = None

    async def _get_service(self):
        if self._service is None:
            from mindflow_backend.services.nlp_embeddings.nlp_embedding_service import (
                NLPEmbeddingService, EmbeddingConfig, EmbeddingMethod,
            )
            config = EmbeddingConfig(method=EmbeddingMethod.TFIDF, max_features=self._dims)
            self._service = NLPEmbeddingService(config)
            await self._service.fit(self._corpus)
        return self._service

    async def embed(self, text: str) -> list[float]:
        svc = await self._get_service()
        result = await svc.generate_embeddings([text])
        vec = result[0]
        # Pad or truncate to self._dims
        if len(vec) < self._dims:
            vec = vec + [0.0] * (self._dims - len(vec))
        return vec[: self._dims]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        svc = await self._get_service()
        results = await svc.generate_embeddings(texts)
        out = []
        for vec in results:
            if len(vec) < self._dims:
                vec = vec + [0.0] * (self._dims - len(vec))
            out.append(vec[: self._dims])
        return out

    def dimension(self) -> int:
        return self._dims

    def backend(self) -> EmbeddingBackend:
        return EmbeddingBackend.TFIDF


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class EmbeddingProviderFactory:
    """Single source of truth for embedding provider instantiation."""

    @classmethod
    def from_settings(cls) -> IEmbeddingProvider:
        from mindflow_backend.infra.config import get_settings
        settings = get_settings()

        backend_str = getattr(settings, "embedding_backend", EmbeddingBackend.GEMINI.value)
        try:
            backend = EmbeddingBackend(backend_str)
        except ValueError:
            _logger.warning("unknown_embedding_backend", value=backend_str, fallback="gemini")
            backend = EmbeddingBackend.GEMINI

        model_name = getattr(settings, "embedding_model_name", None)
        dims = getattr(settings, "embedding_dims", 768)
        api_key = getattr(settings, "google_api_key", None)

        return cls.create(backend, model_name=model_name, dims=dims, api_key=api_key)

    @classmethod
    def create(
        cls,
        backend: EmbeddingBackend,
        *,
        model_name: str | None = None,
        dims: int = 768,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> IEmbeddingProvider:
        if backend == EmbeddingBackend.GEMINI:
            return GeminiProvider(
                model_name=model_name or "models/text-embedding-004",
                dims=dims,
                api_key=api_key,
            )
        if backend == EmbeddingBackend.OPENAI:
            return OpenAIProvider(model_name=model_name or "text-embedding-3-small", dims=dims, api_key=api_key)
        if backend == EmbeddingBackend.OLLAMA:
            return OllamaProvider(model_name=model_name or "nomic-embed-text", dims=dims, base_url=base_url)
        if backend == EmbeddingBackend.SENTENCE_TRANSFORMER:
            return SentenceTransformerProvider(model_name=model_name or "all-MiniLM-L6-v2", dims=dims)
        if backend == EmbeddingBackend.TFIDF:
            return TFIDFProvider(dims=dims)
        if backend == EmbeddingBackend.HYBRID:
            return SentenceTransformerProvider(model_name=model_name or "all-MiniLM-L6-v2", dims=dims)
        # HASH_FALLBACK or unknown
        return HashFallbackProvider(dims=dims)


@lru_cache(maxsize=1)
def get_embedding_provider() -> IEmbeddingProvider:
    """Singleton embedding provider loaded from settings."""
    try:
        provider = EmbeddingProviderFactory.from_settings()
        _logger.info("embedding_provider_initialized", backend=provider.backend().value)
        return provider
    except Exception as exc:
        _logger.warning("embedding_provider_init_failed_using_hash_fallback", error=str(exc))
        return HashFallbackProvider()
