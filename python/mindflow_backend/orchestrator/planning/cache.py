"""Cache for planning trigger decisions."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.planning import PlanningDecision

_logger = get_logger(__name__)


class PlanningDecisionCache:
    """Cache planning decisions for similar messages."""
    
    def __init__(self, ttl: timedelta = timedelta(hours=1)):
        self._cache: dict[str, tuple[PlanningDecision, datetime]] = {}
        self._ttl = ttl
    
    def _hash_message(self, message: str) -> str:
        """Create hash of message for cache key."""
        normalized = message.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def get(self, message: str) -> PlanningDecision | None:
        """Get cached decision if available and not expired."""
        key = self._hash_message(message)
        
        if key not in self._cache:
            return None
        
        decision, cached_at = self._cache[key]
        
        # Check if expired
        if datetime.now(UTC) - cached_at > self._ttl:
            del self._cache[key]
            _logger.debug("cache_expired", key=key)
            return None
        
        _logger.info("cache_hit", key=key, confidence=decision.confidence)
        return decision
    
    def set(self, message: str, decision: PlanningDecision) -> None:
        """Cache a decision."""
        key = self._hash_message(message)
        self._cache[key] = (decision, datetime.now(UTC))
        
        _logger.debug("cache_set", key=key, confidence=decision.confidence)
    
    def clear(self) -> None:
        """Clear all cached decisions."""
        self._cache.clear()
        _logger.info("cache_cleared")
    
    def size(self) -> int:
        """Get number of cached decisions."""
        return len(self._cache)


_cache: PlanningDecisionCache | None = None


def get_decision_cache() -> PlanningDecisionCache:
    """Get or create the global decision cache instance."""
    global _cache
    if _cache is None:
        _cache = PlanningDecisionCache()
    return _cache
