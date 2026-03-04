from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.session.contracts import RetrievedContext
from omnimind_backend.services.session_review_service import get_session_review_service
from omnimind_backend.services.vector_manager import get_vector_manager
from omnimind_backend.storage.models import (
    AgentMemoryCursor,
    AgentMemoryEmbedding,
    AgentMemoryEvent,
    AgentMemoryFact,
    AgentMemoryWindow,
    SessionEmbedding,
)

_logger = get_logger(__name__)


def estimate_token_count(text: str) -> int:
    """Fast token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _embed_text_llm(text: str, dims: int) -> list[float]:
    """Generate real semantic embeddings using the configured LLM provider.

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

    return _embed_text_hash_fallback(text, dims)


def _embed_text_hash_fallback(text: str, dims: int) -> list[float]:
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


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


@dataclass(slots=True)
class MemoryRetrievalResult:
    context: str
    references: list[str]


class AgentMemoryService:
    """Per-agent rolling memory with summary windows and retrieval."""

    def __init__(
        self,
        *,
        summary_window_tokens: int | None = None,
        retrieval_top_k: int | None = None,
        embedding_dims: int | None = None,
    ) -> None:
        settings = get_settings()
        self.summary_window_tokens = summary_window_tokens or settings.memory_summary_window_tokens
        self.retrieval_top_k = retrieval_top_k or settings.memory_retrieval_top_k
        self.embedding_dims = embedding_dims or settings.memory_embedding_dims
        self.session_review_service = get_session_review_service()

    def record_message(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None = None,
    ) -> None:
        token_count = estimate_token_count(content)
        if token_count <= 0:
            return

        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        db.flush()

        cursor = self._get_or_create_cursor(db, session_id=session_id, agent_id=agent_id)
        cursor.token_total += token_count
        cursor.tokens_since_summary += token_count

        # Update session review service if enabled
        settings = get_settings()
        if settings.enable_session_review_agent:
            try:
                # Schedule async update without blocking
                import asyncio
                from omnimind_backend.schemas.session.review import WindowSize
                
                # Initialize session review if not already done
                if not self.session_review_service.get_active_tracker(session_id):
                    # Schedule initialization for later if we're not in async context
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # We're in an async context, schedule for later
                            loop.call_soon(
                                lambda: asyncio.create_task(
                                    self.session_review_service.initialize_session_review(
                                        session_id,
                                        window_size=WindowSize.MEDIUM,
                                    )
                                )
                            )
                        else:
                            # No loop running, create one
                            asyncio.run(
                                self.session_review_service.initialize_session_review(
                                    session_id,
                                    window_size=WindowSize.MEDIUM,
                                )
                            )
                    except RuntimeError:
                        # No event loop, skip session review update
                        pass
                
                # Schedule token count update
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.call_soon(
                            lambda: asyncio.create_task(
                                self.session_review_service.update_token_count(session_id, token_count)
                            )
                        )
                except RuntimeError:
                    # No event loop, skip
                    pass
                
            except Exception as exc:
                _logger.warning(
                    "session_review_update_failed",
                    error=str(exc),
                    session_id=session_id,
                    agent_id=agent_id,
                )

        if cursor.tokens_since_summary >= self.summary_window_tokens:
            self._summarize_pending_window(
                db,
                session_id=session_id,
                agent_id=agent_id,
                cursor=cursor,
                event_end_id=event.id,
            )

    def retrieve_context_for_query(
        self,
        *,
        db: Session,
        session_id: str,
        agent_id: str,
        query: str,
    ) -> MemoryRetrievalResult:
        return self.retrieve_context(db, session_id=session_id, agent_id=agent_id, query=query)

    def retrieve_context(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        query: str,
    ) -> MemoryRetrievalResult:
        query_vec = _embed_text_llm(query, self.embedding_dims)

        embeddings = list(
            db.scalars(
                select(AgentMemoryEmbedding)
                .where(
                    AgentMemoryEmbedding.session_id == session_id,
                    AgentMemoryEmbedding.agent_id == agent_id,
                )
                .order_by(AgentMemoryEmbedding.id.desc())
                .limit(512)
            )
        )

        ranked: list[tuple[float, AgentMemoryEmbedding]] = []
        for row in embeddings:
            score = _cosine_similarity(query_vec, row.vector)
            ranked.append((score, row))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = [row for _, row in ranked[: self.retrieval_top_k] if row.content_excerpt.strip()]

        if not selected:
            windows = list(
                db.scalars(
                    select(AgentMemoryWindow)
                    .where(
                        AgentMemoryWindow.session_id == session_id,
                        AgentMemoryWindow.agent_id == agent_id,
                    )
                    .order_by(AgentMemoryWindow.id.desc())
                    .limit(self.retrieval_top_k)
                )
            )
            context = "\n\n".join(
                f"[window:{w.window_index}] {w.summary_md}" for w in windows if w.summary_md.strip()
            )
            refs = [f"window:{w.window_index}" for w in windows]
            return MemoryRetrievalResult(context=context, references=refs)

        blocks: list[str] = []
        refs: list[str] = []
        for item in selected:
            refs.append(f"{item.source_type}:{item.source_id}")
            blocks.append(f"[{item.source_type}:{item.source_id}] {item.content_excerpt}")

        return MemoryRetrievalResult(context="\n\n".join(blocks), references=refs)

    def _get_or_create_cursor(self, db: Session, *, session_id: str, agent_id: str) -> AgentMemoryCursor:
        cursor = db.scalar(
            select(AgentMemoryCursor).where(
                AgentMemoryCursor.session_id == session_id,
                AgentMemoryCursor.agent_id == agent_id,
            )
        )
        if cursor:
            return cursor

        cursor = AgentMemoryCursor(
            session_id=session_id,
            agent_id=agent_id,
            token_total=0,
            tokens_since_summary=0,
            window_index=0,
            last_summarized_event_id=None,
        )
        db.add(cursor)
        db.flush()
        return cursor

    def _summarize_pending_window(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        cursor: AgentMemoryCursor,
        event_end_id: int,
    ) -> None:
        start_event_id = (cursor.last_summarized_event_id or 0) + 1
        events = list(
            db.scalars(
                select(AgentMemoryEvent)
                .where(
                    AgentMemoryEvent.session_id == session_id,
                    AgentMemoryEvent.agent_id == agent_id,
                    AgentMemoryEvent.id >= start_event_id,
                    AgentMemoryEvent.id <= event_end_id,
                )
                .order_by(AgentMemoryEvent.id.asc())
            )
        )
        if not events:
            return

        summary_md, key_points = self._build_structured_summary(events)
        checksum_input = "\n".join(f"{e.id}:{e.content}" for e in events).encode("utf-8")
        checksum = hashlib.sha256(checksum_input).hexdigest()

        window = AgentMemoryWindow(
            session_id=session_id,
            agent_id=agent_id,
            window_index=cursor.window_index + 1,
            token_start=cursor.token_total - cursor.tokens_since_summary + 1,
            token_end=cursor.token_total,
            event_start_id=events[0].id,
            event_end_id=events[-1].id,
            summary_md=summary_md,
            key_points=key_points,
            coverage_ratio=1.0,
            checksum=checksum,
        )
        db.add(window)
        db.flush()

        self._store_embedding(
            db,
            session_id=session_id,
            agent_id=agent_id,
            source_type="window",
            source_id=window.id,
            content_excerpt=summary_md,
        )

        for point in key_points[:8]:
            fact = AgentMemoryFact(
                session_id=session_id,
                agent_id=agent_id,
                window_id=window.id,
                fact_type="insight",
                content=point,
                weight=1.0,
            )
            db.add(fact)
            db.flush()
            self._store_embedding(
                db,
                session_id=session_id,
                agent_id=agent_id,
                source_type="fact",
                source_id=fact.id,
                content_excerpt=point,
            )

        cursor.window_index += 1
        cursor.tokens_since_summary = 0
        cursor.last_summarized_event_id = event_end_id

    def _build_structured_summary(self, events: list[AgentMemoryEvent]) -> tuple[str, list[str]]:
        timeline: list[str] = []
        for event in events[:18]:
            compact = re.sub(r"\s+", " ", event.content).strip()
            compact = compact[:280]
            timeline.append(f"- [{event.role}] {compact}")

        candidate_sentences: list[str] = []
        for event in events:
            for sentence in re.split(r"[\n\.;:!?]", event.content):
                compact = re.sub(r"\s+", " ", sentence).strip()
                if len(compact) >= 24:
                    candidate_sentences.append(compact)

        key_points: list[str] = []
        seen: set[str] = set()
        for sentence in candidate_sentences:
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            key_points.append(sentence[:240])
            if len(key_points) >= 10:
                break

        if not key_points and timeline:
            key_points = [line[11:] for line in timeline[:3]]

        summary_lines = [
            "Consolidated summary of the agent context window:",
            f"- Total events: {len(events)}",
            "- Main timeline:",
            *timeline,
        ]
        if key_points:
            summary_lines.append("- Key points:")
            summary_lines.extend(f"  - {item}" for item in key_points[:8])

        return "\n".join(summary_lines), key_points

    def _store_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        source_type: str,
        source_id: int,
        content_excerpt: str,
    ) -> None:
        embedding = AgentMemoryEmbedding(
            session_id=session_id,
            agent_id=agent_id,
            source_type=source_type,
            source_id=source_id,
            content_excerpt=content_excerpt[:1500],
            vector=_embed_text_llm(content_excerpt, self.embedding_dims),
        )
        db.add(embedding)

    async def retrieve_context_for_query(
        self,
        db: Session,
        *,
        session_id: str,
        agent_id: str,
        query: str,
        top_k: int = 4,
        min_score: float = 0.3,
    ) -> RetrievedContext:
        """
        Retrieve relevant context for a query using vector search.
        
        Args:
            db: Database session
            session_id: Session identifier
            agent_id: Agent identifier
            query: Search query
            top_k: Maximum number of results
            min_score: Minimum relevance score
            
        Returns:
            RetrievedContext with relevant information
        """
        _logger.info(
            "vector_context_retrieval_started",
            session_id=session_id,
            agent_id=agent_id,
            query=query,
            top_k=top_k,
        )
        
        try:
            # Get vector manager
            vector_manager = await get_vector_manager()
            
            # Generate query embedding
            query_vector = _embed_text_llm(query, self.embedding_dims)
            
            # Search for similar vectors
            search_results = await vector_manager.search_session_context(
                session_id=session_id,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=min_score,
            )
            
            # Format results into context
            context_parts = [f"Context for query: {query}"]
            source_sessions = []
            
            for result in search_results:
                # TODO: Format actual search results
                context_parts.append(f"- {result.get('content', 'No content available')}")
                source_sessions.append(session_id)  # TODO: Extract from result metadata
            
            context_content = "\n\n".join(context_parts)
            
            retrieved_context = RetrievedContext(
                context_id=self._generate_context_id(),
                session_id=session_id,
                query=query,
                context_windows=[(0, 10000)],  # TODO: Extract from results
                content=context_content,
                relevance_score=0.8,  # TODO: Calculate from search results
                source_sessions=source_sessions,
                metadata={
                    "agent_id": agent_id,
                    "retrieval_method": "vector_search",
                    "results_count": len(search_results),
                },
            )
            
            _logger.info(
                "vector_context_retrieval_completed",
                session_id=session_id,
                agent_id=agent_id,
                results_count=len(search_results),
            )
            
            return retrieved_context
            
        except Exception as exc:
            _logger.error(
                "vector_context_retrieval_failed",
                session_id=session_id,
                agent_id=agent_id,
                error=str(exc),
            )
            # Fallback to basic context
            return RetrievedContext(
                context_id=self._generate_context_id(),
                session_id=session_id,
                query=query,
                context_windows=[(0, 10000)],
                content=f"Unable to retrieve vector context for query: {query}",
                relevance_score=0.0,
                source_sessions=[session_id],
                metadata={"agent_id": agent_id, "retrieval_method": "fallback"},
            )
    
    async def store_session_embedding(
        self,
        db: Session,
        *,
        session_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """
        Store content embedding for session context retrieval.
        
        Args:
            db: Database session
            session_id: Session identifier
            content: Content to embed and store
            metadata: Additional metadata
            
        Returns:
            Embedding ID
        """
        _logger.info(
            "session_embedding_storage_started",
            session_id=session_id,
            content_length=len(content),
        )
        
        try:
            # Get vector manager
            vector_manager = await get_vector_manager()
            
            # Create collection for session if needed
            await vector_manager.create_session_collection(session_id)
            
            # Generate embedding
            embedding_vector = _embed_text_llm(content, self.embedding_dims)
            
            # Store in vector database
            embedding_data = {
                "content": content,
                "vector": embedding_vector,
                "metadata": metadata or {},
            }
            
            vector_ids = await vector_manager.store_session_embeddings(
                session_id=session_id,
                embeddings=[embedding_data],
            )
            
            # Also store in local database for backup
            session_embedding = SessionEmbedding(
                session_id=session_id,
                content=content,
                embedding=embedding_vector,
                metadata=metadata or {},
            )
            db.add(session_embedding)
            db.commit()
            
            embedding_id = vector_ids[0] if vector_ids else str(session_embedding.id)
            
            _logger.info(
                "session_embedding_stored",
                session_id=session_id,
                embedding_id=embedding_id,
            )
            
            return embedding_id
            
        except Exception as exc:
            _logger.error(
                "session_embedding_storage_failed",
                session_id=session_id,
                error=str(exc),
            )
            raise
    
    def _generate_context_id(self) -> str:
        """Generate a unique context ID."""
        return f"context_{hash(str(os.urandom(16)))}"


@lru_cache(maxsize=1)
def get_memory_service() -> AgentMemoryService:
    return AgentMemoryService()
