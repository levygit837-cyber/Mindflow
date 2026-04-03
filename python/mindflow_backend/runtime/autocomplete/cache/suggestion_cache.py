"""LRU Cache for autocomplete suggestions.

Provides TTL-based caching with automatic invalidation.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Entrada do cache."""
    value: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        """Verifica se a entrada expirou."""
        return time.time() - self.timestamp > self.ttl


class SuggestionCache:
    """Cache LRU para sugestões de autocomplete.

    Attributes:
        ttl: TTL padrão em segundos (60s)
        max_entries: Máximo de entradas no cache (1000)

    Usage:
        cache = SuggestionCache(ttl=60.0, max_entries=1000)

        # Armazenar
        cache.set("query_key", suggestions_list)

        # Recuperar
        suggestions = cache.get("query_key")
    """

    def __init__(self, ttl: float = 60.0, max_entries: int = 1000) -> None:
        self.ttl = ttl
        self.max_entries = max_entries
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """Recupera valor do cache.

        Args:
            key: Chave do cache

        Returns:
            Valor cached ou None se não encontrado/expirado
        """
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            return None

        # Mover para o final (mais recente)
        self._cache.move_to_end(key)
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Armazena valor no cache.

        Args:
            key: Chave do cache
            value: Valor a armazenar
            ttl: TTL específico (usa padrão se None)
        """
        # Se já existe, atualizar
        if key in self._cache:
            self._cache.move_to_end(key)

        # Se excedeu max_entries, remover o mais antigo
        while len(self._cache) >= self.max_entries:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(
            value=value,
            timestamp=time.time(),
            ttl=ttl if ttl is not None else self.ttl,
        )

    def invalidate(self, key: str) -> bool:
        """Invalida uma entrada do cache.

        Args:
            key: Chave a invalidar

        Returns:
            True se encontrou e removeu
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
        _logger.debug("cache_cleared")

    def cleanup_expired(self) -> int:
        """Remove entradas expiradas.

        Returns:
            Número de entradas removidas
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)

    @property
    def size(self) -> int:
        """Número de entradas no cache."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Taxa de acerto do cache."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict[str, Any]:
        """Retorna estatísticas do cache."""
        return {
            "size": self.size,
            "max_entries": self.max_entries,
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 4),
        }