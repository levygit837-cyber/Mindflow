"""Agentic memory store using LangGraph AsyncPostgresStore.

Provides a hierarchical, persistent fact store across sessions and threads.

Fact taxonomy (4 namespaces):
  FACT      - Declarative factual knowledge ("PostgreSQL versão 16 é o DB principal")
  ABOUT     - User profile, preferences, working style ("Prefere async, senior backend dev")
  PROCEDURE - Learned behavioral patterns ("Sempre mostrar código antes de explicar")
  CONTEXT   - Active project/domain context ("Branch: feat/memory-refactor")
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

VALID_FACT_TYPES = frozenset({"fact", "about", "procedure", "context"})

# Namespace mapping: fact_type → plural namespace segment
_NS_MAP = {
    "fact": "facts",
    "about": "abouts",
    "procedure": "procedures",
    "context": "contexts",
}


def _namespace(fact_type: str, user_id: str) -> tuple[str, ...]:
    return ("agent", user_id, _NS_MAP[fact_type])


@asynccontextmanager
async def langgraph_store():
    """Context manager providing AsyncPostgresStore for agentic memory."""
    from mindflow_backend.infra.config import get_settings
    from langgraph.store.postgres import AsyncPostgresStore

    settings = get_settings()
    async with AsyncPostgresStore.from_conn_string(settings.database.url) as store:
        await store.setup()
        yield store


class AgenticMemoryStore:
    """Hierarchical persistent fact store wrapping LangGraph AsyncPostgresStore.

    Usage::

        async with langgraph_store() as store:
            mem = AgenticMemoryStore(store)
            await mem.put_fact(user_id="u1", fact_type="about", key="language", value="Python")
            results = await mem.search_facts(user_id="u1", query="programming language")
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    async def put_fact(
        self,
        *,
        user_id: str,
        fact_type: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source_session_id: str | None = None,
    ) -> None:
        """Store or update a hierarchical fact.

        Args:
            user_id: User or agent identifier (scopes the namespace).
            fact_type: One of "fact", "about", "procedure", "context".
            key: Unique key within namespace, e.g. "python_version".
            value: Text content of the fact.
            confidence: Confidence score [0.0–1.0].
            source_session_id: Optional session that produced this fact.
        """
        if fact_type not in VALID_FACT_TYPES:
            raise ValueError(f"fact_type must be one of {sorted(VALID_FACT_TYPES)}, got {fact_type!r}")

        ns = _namespace(fact_type, user_id)
        payload = {
            "value": value,
            "fact_type": fact_type,
            "confidence": confidence,
        }
        if source_session_id:
            payload["source_session_id"] = source_session_id

        await self._store.aput(ns, key, payload)
        _logger.debug("agentic_fact_stored", fact_type=fact_type, key=key, user_id=user_id)

    async def get_fact(
        self,
        *,
        user_id: str,
        fact_type: str,
        key: str,
    ) -> dict | None:
        """Retrieve a specific fact by key.

        Returns the payload dict or None if not found.
        """
        if fact_type not in VALID_FACT_TYPES:
            raise ValueError(f"fact_type must be one of {sorted(VALID_FACT_TYPES)}")
        ns = _namespace(fact_type, user_id)
        item = await self._store.aget(ns, key)
        return item.value if item else None

    async def search_facts(
        self,
        *,
        user_id: str,
        query: str,
        fact_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Semantic search across fact namespaces.

        Args:
            user_id: User/agent scope.
            query: Natural language query.
            fact_type: Restrict to a specific type, or None to search all.
            limit: Max results per namespace (when searching all, total may be up to 4×limit).

        Returns:
            List of dicts with keys: key, value, fact_type, confidence, score.
        """
        types_to_search = [fact_type] if fact_type else list(VALID_FACT_TYPES)
        results: list[dict] = []

        for ft in types_to_search:
            ns = _namespace(ft, user_id)
            try:
                hits = await self._store.asearch(ns, query=query, limit=limit)
                for hit in hits:
                    payload = hit.value if hasattr(hit, "value") else {}
                    results.append({
                        "key": hit.key,
                        "value": payload.get("value", ""),
                        "fact_type": ft,
                        "confidence": payload.get("confidence", 1.0),
                        "score": getattr(hit, "score", None),
                        "source_session_id": payload.get("source_session_id"),
                    })
            except Exception as exc:
                _logger.warning("agentic_fact_search_failed", fact_type=ft, error=str(exc))

        # Sort by score descending when scores available
        results.sort(key=lambda r: r.get("score") or 0.0, reverse=True)
        return results

    async def list_facts(
        self,
        *,
        user_id: str,
        fact_type: str | None = None,
    ) -> list[dict]:
        """List all facts of a given type (or all types).

        Returns:
            List of dicts with keys: key, value, fact_type, confidence.
        """
        types_to_list = [fact_type] if fact_type else list(VALID_FACT_TYPES)
        results: list[dict] = []

        for ft in types_to_list:
            ns = _namespace(ft, user_id)
            try:
                items = await self._store.alist(ns)
                for item in items:
                    payload = item.value if hasattr(item, "value") else {}
                    results.append({
                        "key": item.key,
                        "value": payload.get("value", ""),
                        "fact_type": ft,
                        "confidence": payload.get("confidence", 1.0),
                        "source_session_id": payload.get("source_session_id"),
                    })
            except Exception as exc:
                _logger.warning("agentic_fact_list_failed", fact_type=ft, error=str(exc))

        return results

    async def delete_fact(
        self,
        *,
        user_id: str,
        fact_type: str,
        key: str,
    ) -> None:
        """Delete a specific fact by key."""
        if fact_type not in VALID_FACT_TYPES:
            raise ValueError(f"fact_type must be one of {sorted(VALID_FACT_TYPES)}")
        ns = _namespace(fact_type, user_id)
        await self._store.adelete(ns, key)
        _logger.debug("agentic_fact_deleted", fact_type=fact_type, key=key, user_id=user_id)
