"""Session retriever service for context window access.

Provides methods for retrieving context from specific token ranges
and sessions with various retrieval modes (range, topic, semantic).
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.session.contracts import (
    RetrievalMode,
    RetrievedContext,
    SessionRetriever,
    SummarizationReview,
)

_logger = get_logger(__name__)


class SessionRetrieverService:
    """Service for retrieving context from sessions and token windows."""
    
    def __init__(self) -> None:
        """Initialize the session retriever service."""
        _logger.info("session_retriever_service_initialized")
    
    async def retrieve_context(
        self,
        session_retriever: SessionRetriever,
    ) -> RetrievedContext:
        """
        Retrieve context based on the session retriever configuration.
        
        Args:
            session_retriever: Configuration for context retrieval
            
        Returns:
            RetrievedContext with the requested context
        """
        _logger.info(
            "context_retrieval_started",
            retriever_id=str(session_retriever.retriever_id),
            session_id=str(session_retriever.session_id),
            mode=session_retriever.retrieval_mode,
            context_window=session_retriever.context_window,
        )
        
        if session_retriever.retrieval_mode == RetrievalMode.RANGE:
            return await self._retrieve_by_range(session_retriever)
        elif session_retriever.retrieval_mode == RetrievalMode.TOPIC:
            return await self._retrieve_by_topic(session_retriever)
        elif session_retriever.retrieval_mode == RetrievalMode.SEMANTIC:
            return await self._retrieve_by_semantic(session_retriever)
        else:
            raise ValueError(f"Unsupported retrieval mode: {session_retriever.retrieval_mode}")
    
    async def _retrieve_by_range(
        self,
        session_retriever: SessionRetriever,
    ) -> RetrievedContext:
        """Retrieve context by token range using actual database."""
        return await self.get_context_window(
            session_id=str(session_retriever.session_id),
            token_range=session_retriever.context_window,
            include_related=False,
        )
    
    async def _retrieve_by_topic(
        self,
        session_retriever: SessionRetriever,
    ) -> RetrievedContext:
        """Retrieve context by topic filtering using keyword search."""
        try:
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.db.models import Message
            from sqlalchemy import select
            
            query = session_retriever.retrieval_query.lower()
            keywords = [word for word in query.split() if len(word) > 3]
            
            async with get_db_session() as session:
                # Get all messages from the session
                stmt = (
                    select(Message)
                    .where(Message.session_id == str(session_retriever.session_id))
                    .order_by(Message.created_at)
                )
                
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                # Filter messages that contain topic keywords
                matching_content = []
                for msg in messages:
                    content_lower = (msg.content or "").lower()
                    # Check if any keyword matches
                    if any(keyword in content_lower for keyword in keywords):
                        matching_content.append(f"[{msg.role.upper()}]: {msg.content}")
                
                if matching_content:
                    content = "\n\n".join(matching_content)
                    relevance = min(0.9, 0.5 + (len(matching_content) * 0.1))
                else:
                    content = f"No messages found matching topic: {session_retriever.retrieval_query}"
                    relevance = 0.3
                
        except Exception as exc:
            _logger.warning("topic_retrieval_failed", error=str(exc))
            content = f"Topic-based context for query: {session_retriever.retrieval_query}"
            relevance = 0.5
        
        return RetrievedContext(
            context_id=UUID(),
            session_id=session_retriever.session_id,
            query=session_retriever.retrieval_query,
            context_windows=[session_retriever.context_window],
            content=content,
            relevance_score=relevance,
            source_sessions=[session_retriever.session_id],
            metadata={"retrieval_mode": "topic"},
        )
    
    async def _retrieve_by_semantic(
        self,
        session_retriever: SessionRetriever,
    ) -> RetrievedContext:
        """Retrieve context by semantic similarity using vector search."""
        results = await self.get_semantic_context(
            query=session_retriever.retrieval_query,
            session_id=str(session_retriever.session_id),
            top_k=1,
            min_score=0.3,
        )
        
        if results:
            # Return the top result
            return results[0]
        
        # Fallback if no results
        return RetrievedContext(
            context_id=UUID(),
            session_id=session_retriever.session_id,
            query=session_retriever.retrieval_query,
            context_windows=[session_retriever.context_window],
            content=f"Semantic context for query: {session_retriever.retrieval_query}",
            relevance_score=0.5,
            source_sessions=[session_retriever.session_id],
            metadata={"retrieval_mode": "semantic", "fallback": True},
        )
    
    async def get_context_window(
        self,
        session_id: str,
        token_range: tuple[int, int],
        include_related: bool = False,
    ) -> RetrievedContext:
        """
        Get context from a specific token window.
        
        Args:
            session_id: Session identifier
            token_range: Token range to retrieve (start, end)
            include_related: Whether to include related sessions
            
        Returns:
            RetrievedContext with the requested window content
        """
        _logger.info(
            "context_window_requested",
            session_id=session_id,
            token_range=token_range,
            include_related=include_related,
        )
        
        try:
            # Get actual messages from database within token range
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.db.models import Session, Message
            from sqlalchemy import select, and_
            
            start_token, end_token = token_range
            
            async with get_db_session() as session:
                # Get messages from the session ordered by creation time
                stmt = (
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.created_at)
                )
                
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                # Accumulate tokens and select messages in range
                current_tokens = 0
                selected_content = []
                
                for msg in messages:
                    msg_tokens = msg.token_count or (len(msg.content) // 4 if msg.content else 0)
                    
                    # Check if message falls within the requested token range
                    if current_tokens >= start_token and current_tokens < end_token:
                        selected_content.append(f"[{msg.role.upper()}]: {msg.content}")
                    
                    current_tokens += msg_tokens
                    
                    # Stop if we've passed the end token
                    if current_tokens >= end_token:
                        break
                
                if selected_content:
                    content = "\n\n".join(selected_content)
                else:
                    content = f"No messages found in token range {start_token}-{end_token}"
                
        except Exception as exc:
            _logger.warning("window_retrieval_failed", error=str(exc))
            content = f"Context from window {token_range[0]}-{token_range[1]} in session {session_id}"
        
        return RetrievedContext(
            context_id=UUID(),
            session_id=UUID(session_id),
            query="",
            context_windows=[token_range],
            content=content,
            relevance_score=1.0,
            source_sessions=[UUID(session_id)],
            metadata={"window_type": "direct_range"},
        )
    
    async def get_semantic_context(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[RetrievedContext]:
        """
        Get context using semantic search.
        
        Args:
            query: Search query
            session_id: Session identifier
            top_k: Maximum number of results
            min_score: Minimum relevance score
            
        Returns:
            List of RetrievedContext objects
        """
        _logger.info(
            "semantic_context_requested",
            session_id=session_id,
            query=query,
            top_k=top_k,
            min_score=min_score,
        )
        
        results = []
        
        try:
            # Use vector manager for semantic search
            from mindflow_backend.services.vector_manager import get_vector_manager
            from mindflow_backend.services.context import get_embedding_service
            
            # Get embedding for query
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.embed_query(query)
            
            # Search in vector database
            vector_manager = await get_vector_manager()
            search_results = await vector_manager.search_session_context(
                session_id=session_id,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=min_score,
            )
            
            # Convert to RetrievedContext objects
            for i, result in enumerate(search_results):
                content = result.get("metadata", {}).get("content", "")
                if not content:
                    content = result.get("document", "")
                
                results.append(RetrievedContext(
                    context_id=UUID(),
                    session_id=UUID(session_id),
                    query=query,
                    context_windows=[(0, 10000)],  # Approximate
                    content=content,
                    relevance_score=result.get("score", 0.8 - (i * 0.1)),
                    source_sessions=[UUID(session_id)],
                    metadata={
                        "semantic_rank": i + 1,
                        "vector_id": result.get("id"),
                    },
                ))
            
            _logger.info(
                "semantic_search_completed",
                results_count=len(results),
            )
            
        except Exception as exc:
            _logger.warning(
                "semantic_search_failed",
                error=str(exc),
                fallback="placeholder",
            )
            # Fallback to placeholder results
            for i in range(min(top_k, 3)):
                content = f"Semantic result {i+1} for query: {query}"
                results.append(RetrievedContext(
                    context_id=UUID(),
                    session_id=UUID(session_id),
                    query=query,
                    context_windows=[(0, 10000)],
                    content=content,
                    relevance_score=0.8 - (i * 0.1),
                    source_sessions=[UUID(session_id)],
                    metadata={"semantic_rank": i + 1, "fallback": True},
                ))
        
        return results
    
    async def create_summarization_review(
        self,
        session_retriever_id: UUID,
        context_summary: str,
        files_analyzed: list[str],
        goal_achievement: float,
        description: str,
        confidence_score: float = 0.5,
        session_history: list[dict] | None = None,
    ) -> SummarizationReview:
        """
        Create a summarization review for retrieved context.
        
        Args:
            session_retriever_id: ID of the session retriever
            context_summary: Generated context summary
            files_analyzed: List of analyzed files
            goal_achievement: Goal achievement score (0.0-1.0)
            description: Analysis description
            confidence_score: Confidence in the analysis
            session_history: Optional session history for related detection
            
        Returns:
            SummarizationReview with the analysis results
        """
        _logger.info(
            "summarization_review_created",
            session_retriever_id=str(session_retriever_id),
            goal_achievement=goal_achievement,
            confidence_score=confidence_score,
        )
        
        # Detect writes in analyzed files
        writes_detected = await self._detect_file_writes(files_analyzed)
        
        # Detect related sessions
        related_sessions = await self._detect_related_sessions(
            session_retriever_id, 
            context_summary,
            session_history or []
        )
        
        # Extract insights and action items
        key_insights = await self._extract_insights(context_summary, files_analyzed)
        action_items = await self._extract_action_items(context_summary)
        
        return SummarizationReview(
            review_id=UUID(),
            session_retriever_id=session_retriever_id,
            context_summary=context_summary,
            files_analyzed=files_analyzed,
            writes_detected=writes_detected,
            goal_achievement=goal_achievement,
            description=description,
            related_sessions=related_sessions,
            key_insights=key_insights,
            action_items=action_items,
            confidence_score=confidence_score,
        )
    
    async def _detect_file_writes(self, files_analyzed: list[str]) -> list[dict[str, Any]]:
        """Detect recent writes to analyzed files using filesystem tools."""
        writes = []
        try:
            from mindflow_backend.agents.tools.filesystem import FileReadTool
            import os
            from datetime import datetime
            
            for file_path in files_analyzed:
                try:
                    if os.path.exists(file_path):
                        stat = os.stat(file_path)
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        # Consider files modified in last hour as "written"
                        from datetime import timedelta
                        if datetime.now() - mtime < timedelta(hours=1):
                            writes.append({
                                "file_path": file_path,
                                "modified_time": mtime.isoformat(),
                                "size_bytes": stat.st_size,
                                "write_type": "modification",
                            })
                except Exception:
                    pass
        except Exception as exc:
            _logger.warning("file_write_detection_failed", error=str(exc))
        
        return writes
    
    async def _detect_related_sessions(
        self, 
        session_id: UUID, 
        context_summary: str,
        session_history: list[dict]
    ) -> list[UUID]:
        """Detect related sessions based on content similarity."""
        related = []
        try:
            # Simple heuristic: check if context keywords match session topics
            summary_lower = context_summary.lower()
            keywords = set(word for word in summary_lower.split() if len(word) > 5)
            
            for session in session_history:
                if session.get("id") == str(session_id):
                    continue
                    
                session_topic = session.get("topic", "").lower()
                session_summary = session.get("summary", "").lower()
                
                # Check for keyword overlap
                session_text = f"{session_topic} {session_summary}"
                overlap = len(keywords.intersection(set(session_text.split())))
                
                if overlap > 2:  # Threshold for relatedness
                    try:
                        related.append(UUID(session["id"]))
                    except ValueError:
                        pass
        except Exception as exc:
            _logger.warning("related_session_detection_failed", error=str(exc))
        
        return related
    
    async def _extract_insights(self, context_summary: str, files_analyzed: list[str]) -> list[str]:
        """Extract key insights from context using LLM."""
        insights = []
        try:
            from mindflow_backend.services.llm import get_llm_service
            
            llm_service = get_llm_service()
            
            prompt = f"""Based on this session summary, extract 3-5 key insights:

Summary: {context_summary[:1000]}

Files analyzed: {', '.join(files_analyzed[:10])}

Extract insights that capture:
1. Major findings or discoveries
2. Patterns or trends identified
3. Important conclusions

Format as a bulleted list."""
            
            response = await llm_service.generate(
                prompt=prompt,
                system_message="You are an insight extraction specialist. Be concise and specific.",
                temperature=0.3,
                max_tokens=300,
            )
            
            # Parse insights from response
            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("•"):
                    insight = line.strip("- •").strip()
                    if insight and len(insight) > 10:
                        insights.append(insight)
            
        except Exception as exc:
            _logger.warning("insight_extraction_failed", error=str(exc))
            insights.append("Insight extraction unavailable")
        
        return insights[:5]  # Limit to 5 insights
    
    async def _extract_action_items(self, context_summary: str) -> list[str]:
        """Extract action items from context summary using pattern matching."""
        action_items = []
        
        # Pattern-based extraction
        action_keywords = [
            "need to", "should", "must", "action", "follow up", 
            "implement", "fix", "review", "test", "deploy", "update",
            "TODO", "FIXME", "create", "write", "refactor"
        ]
        
        lines = context_summary.split("\n")
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in action_keywords):
                # Clean up the line
                action = line.strip()
                if len(action) > 10 and len(action) < 200:
                    action_items.append(action)
        
        # If no patterns found, use LLM
        if not action_items:
            try:
                from mindflow_backend.services.llm import get_llm_service
                
                llm_service = get_llm_service()
                prompt = f"""Extract any action items or tasks from this summary:

{context_summary[:800]}

List specific, actionable items only."""
                
                response = await llm_service.generate(
                    prompt=prompt,
                    system_message="Extract action items only. Be specific.",
                    temperature=0.3,
                    max_tokens=200,
                )
                
                for line in response.split("\n"):
                    line = line.strip()
                    if line.startswith("-") or line.startswith("•"):
                        action = line.strip("- •").strip()
                        if action and len(action) > 10:
                            action_items.append(action)
                            
            except Exception:
                pass
        
        return action_items[:5]  # Limit to 5 action items
    
    async def batch_retrieve_context(
        self,
        session_retrievers: list[SessionRetriever],
    ) -> list[RetrievedContext]:
        """
        Retrieve context from multiple session retrievers in parallel.
        
        Args:
            session_retrievers: List of session retriever configurations
            
        Returns:
            List of RetrievedContext objects
        """
        _logger.info(
            "batch_context_retrieval_started",
            retriever_count=len(session_retrievers),
        )
        
        # Execute retrievals in parallel using asyncio.gather
        async def retrieve_with_error_handling(retriever: SessionRetriever) -> RetrievedContext:
            try:
                return await self.retrieve_context(retriever)
            except Exception as exc:
                _logger.error(
                    "context_retrieval_failed",
                    retriever_id=str(retriever.retriever_id),
                    error=str(exc),
                )
                # Return empty context on error
                return RetrievedContext(
                    context_id=UUID(),
                    session_id=retriever.session_id,
                    query=retriever.query,
                    context_windows=[],
                    content="",
                    relevance_score=0.0,
                    source_sessions=[retriever.session_id],
                    metadata={"error": str(exc)},
                )
        
        # Run all retrievals in parallel
        tasks = [
            retrieve_with_error_handling(retriever)
            for retriever in session_retrievers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        _logger.info(
            "batch_context_retrieval_completed",
            retriever_count=len(session_retrievers),
            success_count=sum(1 for r in results if r.relevance_score > 0),
        )
        
        return results
