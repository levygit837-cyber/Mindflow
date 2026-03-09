"""Session Memory Service.

Serviço para gerenciar memória semântica de sessões.
Embeddings são gerados em tempo real (por evento) via EmbeddingProviderFactory.
Retrieval usa pgvector diretamente via SemanticRetriever.
LLM-based chunking foi removido.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.session_memory.models import SessionEmbedding
from mindflow_backend.interfaces.services.memory import AgentMemoryServiceInterface as MemoryServiceInterface
from mindflow_backend.schemas.memory.contracts import MemoryRetrievalResult
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.utils.core import estimate_token_count

_logger = get_logger(__name__)


class SessionMemoryService(BaseAbstractService, MemoryServiceInterface):
    """Serviço para gerenciar memória de sessão com embeddings em tempo real."""

    def __init__(
        self,
        *,
        retrieval_top_k: Optional[int] = None,
    ) -> None:
        super().__init__()
        settings = get_settings()
        self.retrieval_top_k = retrieval_top_k or getattr(settings, "session_retrieval_top_k", 5)

    def _get_logger(self) -> Any:
        return _logger

    async def store_session_event(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        token_start: Optional[int] = None,
        token_end: Optional[int] = None,
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

        embedding_id = await self._store_session_embedding(
            db=db,
            session_id=session_id,
            content=content,
            metadata={"role": role, "stored_at": datetime.now(UTC).isoformat()},
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
        """Recuperar contexto de sessão via pgvector."""
        self.log_operation(
            "retrieve_session_context",
            session_id=session_id,
            query=query,
            cross_session=cross_session,
        )
        try:
            from mindflow_backend.memory.shared.retrieval.semantic import SemanticRetriever
            retriever = SemanticRetriever()
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
                    metadata={"session_id": session_id, "error": "No context found"},
                )

            context_parts = [f"Context for session {session_id}:"]
            references = []
            for hit in hits:
                context_parts.append(f"- {hit.content_excerpt}")
                references.append(f"session_embedding:{hit.source_id}")

            return MemoryRetrievalResult(
                context="\n".join(context_parts),
                references=references,
                metadata={
                    "session_id": session_id,
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

    async def _store_session_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Gerar embedding e persistir em session_embeddings (pgvector)."""
        from mindflow_backend.memory.shared.embeddings.factory import get_embedding_provider
        provider = get_embedding_provider()
        try:
            vector = await provider.embed(content)
        except Exception as exc:
            _logger.warning("session_embed_failed", error=str(exc))
            vector = [0.0] * provider.dimension()

        session_embedding = SessionEmbedding(
            session_id=session_id,
            content=content[:1500],
            embedding=vector,
            session_metadata=metadata or {},
        )
        db.add(session_embedding)
        db.flush()

        embedding_id = str(session_embedding.id)
        _logger.info("session_embedding_stored", embedding_id=embedding_id, session_id=session_id)
        return embedding_id
