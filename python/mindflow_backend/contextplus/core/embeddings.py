# Multi-provider vector embedding engine with cosine similarity search
# FEATURE: Embedding generation and caching for semantic search

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

CACHE_DIR = ".mindflow_contextplus"
EMBEDDINGS_CACHE_FILE = "embeddings-cache.json"


@dataclass
class EmbeddingCacheEntry:
    """A single cached embedding entry."""

    hash: str
    vector: list[float]


@dataclass
class SearchDocument:
    """A document indexed for semantic search."""

    path: str
    header: str
    symbols: list[str]
    content: str


@dataclass
class SearchResult:
    """A single search result."""

    path: str
    score: float
    semantic_score: float
    keyword_score: float
    header: str
    matched_symbols: list[str]


def _hash_content(text: str) -> str:
    """Generate a hash for content caching."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _get_cache_dir(root_dir: str) -> str:
    """Get the cache directory path."""
    return os.path.join(root_dir, CACHE_DIR)


def _get_cache_path(root_dir: str) -> str:
    """Get the embeddings cache file path."""
    return os.path.join(_get_cache_dir(root_dir), EMBEDDINGS_CACHE_FILE)


async def _load_cache(root_dir: str) -> dict[str, EmbeddingCacheEntry]:
    """Load embedding cache from disk."""
    cache_path = _get_cache_path(root_dir)
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {k: EmbeddingCacheEntry(**v) for k, v in raw.items()}
    except Exception:
        pass
    return {}


async def _save_cache(root_dir: str, cache: dict[str, EmbeddingCacheEntry]) -> None:
    """Save embedding cache to disk."""
    cache_dir = _get_cache_dir(root_dir)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = _get_cache_path(root_dir)

    raw = {k: {"hash": v.hash, "vector": v.vector} for k, v in cache.items()}
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(raw, f)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    arr_a = np.array(a)
    arr_b = np.array(b)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(arr_a, arr_b) / (norm_a * norm_b))


def _keyword_overlap(text: str, query: str) -> float:
    """Compute keyword overlap score."""
    text_lower = text.lower()
    query_lower = query.lower()
    query_words = set(query_lower.split())
    if not query_words:
        return 0.0
    matches = sum(1 for w in query_words if w in text_lower)
    return matches / len(query_words)


async def fetch_embedding(text: str, provider: str = "ollama") -> list[float]:
    """Fetch embedding from provider (Ollama or OpenAI-compatible).

    Args:
        text: Text to embed
        provider: Embedding provider ("ollama" or "openai")

    Returns:
        Embedding vector as list of floats
    """
    try:
        if provider == "openai":
            import httpx

            api_key = os.environ.get("CONTEXTPLUS_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
            base_url = os.environ.get("CONTEXTPLUS_OPENAI_BASE_URL", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
            model = os.environ.get("CONTEXTPLUS_OPENAI_EMBED_MODEL", os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small"))

            url = f"{base_url.rstrip('/')}/embeddings"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                    json={"model": model, "input": [text]},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        else:
            import ollama

            model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
            host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            client = ollama.AsyncClient(host=host)
            response = await client.embeddings(model=model, prompt=text)
            return response["embedding"]
    except Exception as e:
        _logger.warning(f"Embedding fetch failed: {e}, using hash fallback")
        return _hash_fallback_embedding(text)


def _hash_fallback_embedding(text: str, dims: int = 768) -> list[float]:
    """Generate a deterministic hash-based embedding as fallback."""
    hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    rng = np.random.RandomState(int.from_bytes(hash_bytes[:4], "big"))
    return rng.randn(dims).tolist()


async def fetch_embeddings_batch(texts: list[str], provider: str = "ollama") -> list[list[float]]:
    """Fetch embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        provider: Embedding provider

    Returns:
        List of embedding vectors
    """
    results: list[list[float]] = []
    for text in texts:
        emb = await fetch_embedding(text, provider)
        results.append(emb)
    return results


def hybrid_score(
    semantic_score: float,
    keyword_score: float,
    semantic_weight: float = 0.72,
    keyword_weight: float = 0.28,
) -> float:
    """Compute hybrid score from semantic and keyword scores."""
    return semantic_weight * semantic_score + keyword_weight * keyword_score


async def search_documents(
    documents: list[SearchDocument],
    query: str,
    query_embedding: list[float],
    top_k: int = 5,
    semantic_weight: float = 0.72,
    keyword_weight: float = 0.28,
) -> list[SearchResult]:
    """Search documents using hybrid semantic + keyword scoring.

    Args:
        documents: List of documents to search
        query: Original query string
        query_embedding: Embedding of the query
        top_k: Number of results to return
        semantic_weight: Weight for semantic similarity
        keyword_weight: Weight for keyword overlap

    Returns:
        List of SearchResult sorted by combined score
    """
    results: list[SearchResult] = []

    for doc in documents:
        doc_text = f"{doc.header} {' '.join(doc.symbols)} {doc.content[:500]}"
        doc_embedding = await fetch_embedding(doc_text)

        semantic_score = _cosine_similarity(query_embedding, doc_embedding)
        keyword_score = _keyword_overlap(f"{doc.header} {doc.content}", query)
        combined = hybrid_score(semantic_score, keyword_score, semantic_weight, keyword_weight)

        if combined > 0:
            results.append(
                SearchResult(
                    path=doc.path,
                    score=combined,
                    semantic_score=semantic_score,
                    keyword_score=keyword_score,
                    header=doc.header,
                    matched_symbols=[s for s in doc.symbols if any(w in s.lower() for w in query.lower().split())],
                )
            )

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]