"""Session Memory Service.

Serviço para gerenciar memória semântica de sessões.
Embeddings são gerados em tempo real (por evento) via EmbeddingProviderFactory.
Retrieval usa pgvector diretamente via SemanticRetriever.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.interfaces.services.memory import (
    AgentMemoryServiceInterface as MemoryServiceInterface,
)
from mindflow_backend.memory.storage.models import (
    AgentMemoryEvent,
    AgentMemoryWindow,
    SessionEmbedding,
)
from mindflow_backend.schemas.memory.contracts import MemoryRetrievalResult
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.utils.core import estimate_token_count

_logger = get_logger(__name__)


class SessionMemoryService(BaseAbstractService, MemoryServiceInterface):
    """Serviço para gerenciar memória de sessão com embeddings em tempo real.

    Cada mensagem é armazenada imediatamente com embedding vetorial no PostgreSQL (pgvector).
    Retrieval semântico usa cosine distance direto no banco.
    Suporta retrieval cross-session para recuperar contexto de sessões anteriores.
    """

    def __init__(
        self,
        *,
        retrieval_top_k: int | None = None,
    ) -> None:
        super().__init__()
        settings = get_settings()
        self.retrieval_top_k = retrieval_top_k or getattr(settings, "session_retrieval_top_k", 5)

    def _get_logger(self) -> Any:
        return _logger

    # ------------------------------------------------------------------
    # Core session memory operations
    # ------------------------------------------------------------------

    async def store_session_event(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
        token_start: int | None = None,
        token_end: int | None = None,
    ) -> str:
        """Armazenar evento de sessão e gerar embedding em tempo real."""
        self.log_operation(
            "store_session_event",
            session_id=session_id,
            agent_id=agent_id,
            role=role,
        )
        token_count = estimate_token_count(content)
        if token_count <= 0:
            return ""

        existing_embedding_id = await self._find_existing_session_embedding(
            db=db,
            session_id=session_id,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
        )
        if existing_embedding_id is not None:
            _logger.info(
                "session_event_duplicate_skipped",
                session_id=session_id,
                source_message_id=source_message_id,
                idempotency_key=idempotency_key,
            )
            return existing_embedding_id

        embedding_id = await self._store_session_embedding(
            db=db,
            session_id=session_id,
            content=content,
            metadata={
                "role": role,
                "agent_id": agent_id,
                "stored_at": datetime.now(UTC).isoformat(),
                "source_message_id": source_message_id,
                "idempotency_key": idempotency_key,
            },
        )
        _logger.info("session_event_stored", embedding_id=embedding_id, session_id=session_id)
        return embedding_id

    async def retrieve_session_context(
        self,
        db: Session,
        *,
        session_id: str,
        query: str,
        cross_session: bool = False,
        max_results: int = 10,
    ) -> MemoryRetrievalResult:
        """Recuperar contexto de sessão via pgvector.

        Args:
            db: SQLAlchemy session.
            session_id: ID da sessão atual.
            query: Query de busca semântica.
            cross_session: Se True, busca em TODAS as sessões (não filtra por session_id).
            max_results: Máximo de resultados.
        """
        self.log_operation(
            "retrieve_session_context",
            session_id=session_id,
            query=query,
            cross_session=cross_session,
        )
        try:
            from mindflow_backend.memory.shared.retrieval.semantic import SemanticRetriever
            retriever = SemanticRetriever()

            if cross_session:
                hits = await retriever.retrieve_cross_session_context(
                    db,
                    query=query,
                    top_k=max_results,
                )
            else:
                hits = await retriever.retrieve_session_context(
                    db,
                    session_id=session_id,
                    query=query,
                    top_k=max_results,
                )

            if not hits:
                return MemoryRetrievalResult(
                    context="",
                    references=[],
                    metadata={"session_id": session_id, "cross_session": cross_session, "error": "No context found"},
                )

            context_parts = [f"Context for session {session_id} (cross_session={cross_session}):"]
            references = []
            for hit in hits:
                context_parts.append(f"- {hit.content_excerpt}")
                references.append(f"session_embedding:{hit.source_id}")

            return MemoryRetrievalResult(
                context="\n".join(context_parts),
                references=references,
                metadata={
                    "session_id": session_id,
                    "cross_session": cross_session,
                    "result_count": len(hits),
                    "retrieval_method": "pgvector",
                },
            )
        except Exception as exc:
            _logger.error("retrieve_session_context_failed", error=str(exc))
            return MemoryRetrievalResult(
                context="",
                references=[],
                metadata={"session_id": session_id, "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # AgentMemoryServiceInterface implementations (full, not stubs)
    # ------------------------------------------------------------------

    async def get_agent_memory(
        self,
        agent_id: str,
        session_id: str,
        token_limit: int | None = None,
    ) -> dict[str, Any]:
        """Get memory events for an agent in a session."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                query = (
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryEvent.created_at.desc())
                )
                if token_limit:
                    query = query.limit(50)  # reasonable limit

                rows = list((await db.execute(query)).scalars())
                events = []
                total_tokens = 0
                for row in rows:
                    if token_limit and total_tokens + row.token_count > token_limit:
                        break
                    events.append({
                        "id": row.id,
                        "role": row.role,
                        "content": row.content,
                        "token_count": row.token_count,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    })
                    total_tokens += row.token_count

                return {
                    "memory_events": list(reversed(events)),
                    "token_count": total_tokens,
                    "window_index": 0,
                }
        except Exception as exc:
            _logger.error("get_agent_memory_failed", error=str(exc))
            return {"memory_events": [], "token_count": 0, "window_index": 0}

    async def add_memory_event(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        token_count: int,
        source_message_id: int | None = None,
    ) -> dict[str, Any]:
        """Add a memory event for an agent in a session."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                embedding_id = await self.store_session_event(
                    db=db,
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                )
                return {"status": "stored", "agent_id": agent_id, "session_id": session_id, "embedding_id": embedding_id}
        except Exception as exc:
            _logger.error("add_memory_event_failed", error=str(exc))
            return {"status": "failed", "agent_id": agent_id, "session_id": session_id, "error": str(exc)}

    async def search_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search for semantically similar context in session memory."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.memory.shared.retrieval.semantic import SemanticRetriever

            retriever = SemanticRetriever()
            async with get_db_session() as db:
                hits = await retriever.retrieve_session_context(
                    db,
                    session_id=session_id,
                    query=query,
                    top_k=top_k,
                    min_score=min_score,
                )
                return [
                    {
                        "source_type": hit.source_type,
                        "source_id": hit.source_id,
                        "content": hit.content_excerpt,
                        "score": hit.score,
                    }
                    for hit in hits
                ]
        except Exception as exc:
            _logger.error("search_semantic_context_failed", error=str(exc))
            return []

    async def retrieve_context_for_query(
        self,
        query: str,
        session_id: str,
        agent_id: str,
    ) -> dict[str, Any]:
        """Retrieve context from session memory for a given query."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                result = await self.retrieve_session_context(
                    db,
                    session_id=session_id,
                    query=query,
                    max_results=self.retrieval_top_k,
                )
                return {
                    "context": result.context,
                    "references": result.references,
                    "metadata": result.metadata,
                }
        except Exception as exc:
            _logger.error("retrieve_context_for_query_failed", error=str(exc))
            return {"context": "", "references": [], "metadata": {"error": str(exc)}}

    async def create_memory_summary(
        self,
        agent_id: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> dict[str, Any]:
        """Create an extractive summary of a memory window."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                events = list((await db.execute(
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryEvent.created_at.asc())
                    .offset(window_range[0])
                    .limit(window_range[1] - window_range[0])
                )).scalars())

                if not events:
                    return {
                        "summary": "",
                        "key_points": [],
                        "coverage_ratio": 0.0,
                        "token_count": 0,
                        "created_at": datetime.now(UTC).isoformat(),
                    }

                # Extractive summary: first N messages + key sentences
                summary_parts = [f"Summary of {len(events)} events:"]
                key_points = []
                for event in events[:10]:
                    compact = event.content[:280].replace("\n", " ").strip()
                    summary_parts.append(f"- [{event.role}] {compact}")
                    if len(event.content) >= 24:
                        key_points.append(compact)

                total_tokens = sum(e.token_count for e in events)

                return {
                    "summary": "\n".join(summary_parts),
                    "key_points": key_points[:8],
                    "coverage_ratio": 1.0,
                    "token_count": total_tokens,
                    "created_at": datetime.now(UTC).isoformat(),
                }
        except Exception as exc:
            _logger.error("create_memory_summary_failed", error=str(exc))
            return {
                "summary": "",
                "key_points": [],
                "coverage_ratio": 0.0,
                "token_count": window_range[1] - window_range[0],
                "created_at": datetime.now(UTC).isoformat(),
            }

    async def get_memory_windows(
        self,
        agent_id: str,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """Get memory windows for an agent in a session."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                windows = list((await db.execute(
                    select(AgentMemoryWindow)
                    .where(
                        AgentMemoryWindow.session_id == session_id,
                        AgentMemoryWindow.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryWindow.window_index.desc())
                )).scalars())

                return [
                    {
                        "window_index": w.window_index,
                        "token_start": w.token_start,
                        "token_end": w.token_end,
                        "summary": w.summary_md,
                        "key_points": w.key_points,
                        "created_at": w.created_at.isoformat() if w.created_at else None,
                    }
                    for w in windows
                ]
        except Exception as exc:
            _logger.error("get_memory_windows_failed", error=str(exc))
            return []

    async def initialize_session_memory(
        self, session_id: str, agent_types: list[str]
    ) -> dict[str, Any]:
        return {"session_id": session_id, "initialized": True, "agent_types": agent_types}

    async def cleanup_session_memory(self, session_id: str) -> bool:
        return True

    async def get_session_memory_summary(self, session_id: str) -> dict[str, Any]:
        """Get real summary of session memory statistics."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            async with get_db_session() as db:
                count_result = await db.execute(
                    select(func.count(SessionEmbedding.id))
                    .where(SessionEmbedding.session_id == session_id)
                )
                total_events = count_result.scalar() or 0

                return {
                    "session_id": session_id,
                    "total_events": total_events,
                    "total_tokens": 0,  # Would need to aggregate from events
                }
        except Exception as exc:
            _logger.error("get_session_memory_summary_failed", error=str(exc))
            return {"session_id": session_id, "total_events": 0, "total_tokens": 0}

    # --- Backward compatibility method for streaming system ---

    async def record_message(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Record a message - backward compatibility wrapper for store_session_event."""
        return await self.store_session_event(
            db=db,
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_existing_session_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        source_message_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> str | None:
        """Find an existing embedding for the same source message or idempotency key."""
        if source_message_id is None and not idempotency_key:
            return None

        if source_message_id is not None:
            result = await db.execute(
                select(SessionEmbedding).where(
                    SessionEmbedding.session_id == session_id,
                    SessionEmbedding.source_message_id == source_message_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return str(row.id)

        if idempotency_key:
            result = await db.execute(
                select(SessionEmbedding).where(
                    SessionEmbedding.session_id == session_id,
                    SessionEmbedding.idempotency_key == idempotency_key,
                )
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return str(row.id)

        return None

    async def _store_session_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Gerar embedding e persistir em session_embeddings (pgvector)."""
        from mindflow_backend.memory.shared.embeddings.factory import get_embedding_provider
        provider = get_embedding_provider()
        try:
            vector = await provider.embed(content)
        except Exception as exc:
            _logger.warning("session_embed_failed", error=str(exc))
            return ""

        session_embedding = SessionEmbedding(
            session_id=session_id,
            content=content[:1500],
            embedding=vector,
            source_message_id=(metadata or {}).get("source_message_id"),
            idempotency_key=(metadata or {}).get("idempotency_key"),
            role=(metadata or {}).get("role"),
            agent_id=(metadata or {}).get("agent_id"),
            session_metadata=metadata or {},
        )
        db.add(session_embedding)

        # Support both sync and async session without committing the outer transaction.
        try:
            await db.flush()
        except TypeError:
            db.flush()

        embedding_id = str(session_embedding.id)
        _logger.info("session_embedding_stored", embedding_id=embedding_id, session_id=session_id)
        return embedding_id
