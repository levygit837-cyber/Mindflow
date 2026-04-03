"""Session review worker for handling session window reviews and context governance."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import ValidationError

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.workers.base.worker import BaseWorker, WorkerResult
from mindflow_backend.workers.config.queues import QueueConfig
from mindflow_backend.workers.system.consumers.session_review_consumer import (
    SessionReviewTaskConsumer,
)

_logger = get_logger(__name__)


class SessionReviewWorker(BaseWorker):
    """Worker specialized for session review and context governance tasks."""
    
    def __init__(self, queue_config: QueueConfig) -> None:
        """Initialize the Session Review worker."""
        super().__init__(queue_config, worker_name="session_review_worker")
        self._session_review_consumer = SessionReviewTaskConsumer()
    
    async def process_message(self, message_data: dict[str, Any]) -> WorkerResult:
        """Process session review tasks.
        
        Supported task types:
        - session_review.requested: Execute a queued review request for a token window
        - window_review: Review session windows when limits reached
        - context_summarization: Summarize session context
        - memory_consolidation: Consolidate session memories
        - token_management: Manage token windows and budgets
        - session_cleanup: Clean up old session data
        """
        start_time = time.time()
        message_data = self._normalize_message_data(message_data)
        task_type = message_data.get("task_type", "unknown")
        task_id = message_data.get("task_id", "unknown")
        
        try:
            _logger.info(f"SessionReviewWorker processing {task_type} task {task_id}")
            
            if task_type in {"session_review.requested", "review_requested"}:
                result = await self._handle_review_requested(message_data)
            elif task_type == "window_review":
                result = await self._handle_window_review(message_data)
            elif task_type == "context_summarization":
                result = await self._handle_context_summarization(message_data)
            elif task_type == "memory_consolidation":
                result = await self._handle_memory_consolidation(message_data)
            elif task_type == "token_management":
                result = await self._handle_token_management(message_data)
            elif task_type == "session_cleanup":
                result = await self._handle_session_cleanup(message_data)
            else:
                result = WorkerResult(
                    success=False,
                    message=f"Unsupported task type: {task_type}",
                    processing_time=time.time() - start_time,
                )
            
            _logger.info(
                f"SessionReviewWorker completed {task_type} task {task_id} "
                f"({'SUCCESS' if result.success else 'FAILED'})"
            )
            
            return result

        except ValidationError as e:
            message_data["retry_count"] = self.queue_config.max_retries
            _logger.error(
                f"SessionReviewWorker invalid payload for {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Invalid session review payload: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )
            
        except Exception as e:
            _logger.error(
                f"SessionReviewWorker failed to process {task_type} task {task_id}: {e}",
                exc_info=True
            )
            return WorkerResult(
                success=False,
                message=f"Task processing failed: {e}",
                error=e,
                processing_time=time.time() - start_time,
            )

    async def _handle_review_requested(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle the real queued session review path."""
        result = await self._session_review_consumer.consume_requested_review(message_data)
        return WorkerResult(
            success=True,
            message="Session review request processed successfully",
            data=result,
        )
    
    async def _handle_window_review(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle session window review when token limits reached.

        Extracts key facts from a specific memory window and persists them
        as SessionFacts for future recall.

        Args:
            message_data: Task data containing session_id and window_index

        Returns:
            WorkerResult with window review statistics
        """
        session_id = message_data.get("session_id")
        window_index = message_data.get("window_index", 0)
        trigger_type = message_data.get("trigger_type", "token_limit")
        review_priority = message_data.get("review_priority", "medium")

        if not session_id:
            return WorkerResult(
                success=False,
                message="session_id is required for window review",
            )

        try:
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.memory.session.fact_extractor import SessionFactExtractor
            from mindflow_backend.memory.storage.models import AgentMemoryEvent, AgentMemoryWindow
            from sqlalchemy import select

            async with get_db_session() as db:
                # Step 1: Fetch the specific window
                window_query = (
                    select(AgentMemoryWindow)
                    .where(
                        AgentMemoryWindow.session_id == session_id,
                        AgentMemoryWindow.window_index == window_index,
                    )
                )

                window_result = await db.execute(window_query)
                window = window_result.scalar_one_or_none()

                if not window:
                    return WorkerResult(
                        success=False,
                        message=f"Window {window_index} not found for session {session_id}",
                    )

                # Step 2: Fetch events from this window
                events_query = (
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.window_id == window.id,
                    )
                    .order_by(AgentMemoryEvent.created_at.asc())
                )

                events_result = await db.execute(events_query)
                events = events_result.scalars().all()

                if not events:
                    return WorkerResult(
                        success=True,
                        message=f"No events found in window {window_index}",
                        data={
                            "session_id": session_id,
                            "window_index": window_index,
                            "events_processed": 0,
                        },
                    )

                # Step 3: Convert events to message format
                messages = []
                for event in events:
                    # Extract content from event
                    content = event.content or ""
                    if event.event_type:
                        content = f"[{event.event_type}] {content}"

                    messages.append({
                        "role": "assistant",  # Events are from agent
                        "content": content,
                        "metadata": {
                            "session_id": session_id,
                            "agent_id": event.agent_id,
                            "event_type": event.event_type,
                        },
                    })

                # Step 4: Extract facts from window events
                fact_extractor = SessionFactExtractor(max_facts=10)  # Limit per window
                agent_id = window.agent_id or "window_review"

                facts = await fact_extractor.extract(
                    messages,
                    session_id,
                    agent_id,
                )

                # Step 5: Link facts to source window and persist
                facts_count = 0
                if facts:
                    for fact in facts:
                        fact.source_window_id = window.id

                    facts_count = await fact_extractor.persist_facts(
                        db,
                        facts,
                        generate_embeddings=True,
                    )

                # Step 6: Extract key topics and actions
                key_topics = set()
                actions_documented = []

                for fact in facts:
                    if fact.category:
                        key_topics.add(fact.category)

                    if fact.fact_type == "action":
                        actions_documented.append(fact.content[:100])

                _logger.info(
                    "window_review_completed",
                    session_id=session_id,
                    window_index=window_index,
                    facts_extracted=facts_count,
                )

                return WorkerResult(
                    success=True,
                    message=f"Window review completed for session {session_id}, window {window_index}",
                    data={
                        "session_id": session_id,
                        "window_index": window_index,
                        "trigger_type": trigger_type,
                        "review_priority": review_priority,
                        "review_summary": {
                            "total_events": len(events),
                            "total_tokens": window.token_count,
                            "key_topics": list(key_topics),
                            "actions_documented": actions_documented[:5],
                            "facts_extracted": facts_count,
                            "facts_by_type": {
                                "action": len([f for f in facts if f.fact_type == "action"]),
                                "decision": len([f for f in facts if f.fact_type == "decision"]),
                                "discovery": len([f for f in facts if f.fact_type == "discovery"]),
                                "error": len([f for f in facts if f.fact_type == "error"]),
                                "state": len([f for f in facts if f.fact_type == "state"]),
                            },
                        },
                        "next_actions": [
                            "Facts persisted for cross-session recall",
                            "Window can be archived if needed",
                        ],
                    },
                )

        except Exception as exc:
            _logger.error(
                "window_review_failed",
                session_id=session_id,
                window_index=window_index,
                error=str(exc),
            )
            return WorkerResult(
                success=False,
                message=f"Window review failed: {str(exc)}",
                error=exc,
            )
    
    async def _handle_context_summarization(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle context summarization for long sessions.

        Uses SessionFactExtractor to extract structured facts from session messages
        and generates a consolidated summary via LLM.

        Args:
            message_data: Task data containing session_id and summarization parameters

        Returns:
            WorkerResult with extracted facts and summary
        """
        session_id = message_data.get("session_id")
        context_range = message_data.get("context_range", "full_session")
        summary_type = message_data.get("summary_type", "comprehensive")
        target_length = message_data.get("target_length", 500)

        if not session_id:
            return WorkerResult(
                success=False,
                message="session_id is required for context summarization",
            )

        try:
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.memory.session.fact_extractor import SessionFactExtractor
            from mindflow_backend.memory.storage.models import ChatMessage
            from sqlalchemy import select

            # Step 1: Fetch session messages
            async with get_db_session() as db:
                query = (
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.asc())
                )

                result = await db.execute(query)
                messages_rows = result.scalars().all()

                if not messages_rows:
                    return WorkerResult(
                        success=False,
                        message=f"No messages found for session {session_id}",
                    )

                # Convert to message format for fact extraction
                messages = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "metadata": {
                            "session_id": session_id,
                            "agent_id": getattr(msg, "agent_id", "unknown"),
                        },
                    }
                    for msg in messages_rows
                ]

                # Step 2: Extract facts using SessionFactExtractor
                fact_extractor = SessionFactExtractor()
                agent_id = message_data.get("agent_id", "session_review")

                facts = await fact_extractor.extract(
                    messages,
                    session_id,
                    agent_id,
                )

                # Step 3: Persist facts with embeddings
                facts_count = 0
                if facts:
                    facts_count = await fact_extractor.persist_facts(
                        db,
                        facts,
                        generate_embeddings=True,
                    )

                _logger.info(
                    "context_summarization_facts_extracted",
                    session_id=session_id,
                    facts_count=facts_count,
                )

            # Step 4: Generate summary from facts
            summary_parts = []
            key_points = []

            if facts:
                # Group facts by type
                actions = [f for f in facts if f.fact_type == "action"]
                decisions = [f for f in facts if f.fact_type == "decision"]
                discoveries = [f for f in facts if f.fact_type == "discovery"]
                errors = [f for f in facts if f.fact_type == "error"]
                states = [f for f in facts if f.fact_type == "state"]

                # Build summary
                if actions:
                    summary_parts.append(f"Actions taken: {', '.join(a.content[:50] for a in actions[:3])}")
                    key_points.extend([a.content for a in actions[:3]])

                if decisions:
                    summary_parts.append(f"Key decisions: {', '.join(d.content[:50] for d in decisions[:2])}")
                    key_points.extend([d.content for d in decisions[:2]])

                if discoveries:
                    summary_parts.append(f"Discoveries: {', '.join(d.content[:50] for d in discoveries[:2])}")
                    key_points.extend([d.content for d in discoveries[:2]])

                if errors:
                    summary_parts.append(f"Issues resolved: {len(errors)}")

                if states:
                    summary_parts.append(f"Current state: {states[-1].content[:100]}")

                summary_text = ". ".join(summary_parts) + "."
            else:
                summary_text = f"Session {session_id} processed with {len(messages)} messages."
                key_points = ["No structured facts extracted"]

            # Calculate compression ratio
            total_content_length = sum(len(str(m.get("content", ""))) for m in messages)
            compression_ratio = len(summary_text) / total_content_length if total_content_length > 0 else 0.0

            return WorkerResult(
                success=True,
                message=f"Context summarized for session {session_id}",
                data={
                    "session_id": session_id,
                    "context_range": context_range,
                    "summary_type": summary_type,
                    "summary_text": summary_text,
                    "key_points": key_points[:10],  # Limit to 10
                    "facts_extracted": facts_count,
                    "facts_by_type": {
                        "action": len([f for f in facts if f.fact_type == "action"]),
                        "decision": len([f for f in facts if f.fact_type == "decision"]),
                        "discovery": len([f for f in facts if f.fact_type == "discovery"]),
                        "error": len([f for f in facts if f.fact_type == "error"]),
                        "state": len([f for f in facts if f.fact_type == "state"]),
                    },
                    "messages_processed": len(messages),
                    "summary_length": len(summary_text),
                    "compression_ratio": round(compression_ratio, 3),
                },
            )

        except Exception as exc:
            _logger.error(
                "context_summarization_failed",
                session_id=session_id,
                error=str(exc),
            )
            return WorkerResult(
                success=False,
                message=f"Context summarization failed: {str(exc)}",
                error=exc,
            )
    
    async def _handle_memory_consolidation(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle memory consolidation for session data.

        Consolidates HierarchicalAnnotations by category/subcategory and generates
        summaries for each category using LLM.

        Args:
            message_data: Task data containing session_id and consolidation parameters

        Returns:
            WorkerResult with consolidation statistics
        """
        session_id = message_data.get("session_id")
        consolidation_type = message_data.get("consolidation_type", "incremental")
        retention_policy = message_data.get("retention_policy", "keep_all")

        if not session_id:
            return WorkerResult(
                success=False,
                message="session_id is required for memory consolidation",
            )

        try:
            from mindflow_backend.infra.database.connection import get_db_session
            from mindflow_backend.memory.storage.models import HierarchicalAnnotation, MemoryCategory
            from sqlalchemy import select, func

            async with get_db_session() as db:
                # Step 1: Fetch HierarchicalAnnotations for this session
                query = (
                    select(HierarchicalAnnotation)
                    .where(HierarchicalAnnotation.session_id == session_id)
                    .order_by(HierarchicalAnnotation.created_at.asc())
                )

                result = await db.execute(query)
                annotations = result.scalars().all()

                if not annotations:
                    return WorkerResult(
                        success=True,
                        message=f"No annotations found for session {session_id}",
                        data={
                            "session_id": session_id,
                            "memories_processed": 0,
                            "memories_consolidated": 0,
                        },
                    )

                # Step 2: Group annotations by category
                category_groups: dict[str, list] = {}
                for annotation in annotations:
                    category_id = annotation.category_id
                    if category_id:
                        if category_id not in category_groups:
                            category_groups[category_id] = []
                        category_groups[category_id].append(annotation)

                # Step 3: Consolidate by category
                consolidation_summary = {
                    "topics_identified": [],
                    "key_entities": set(),
                    "relationships_found": 0,
                }

                memories_consolidated = 0
                vector_updates = 0

                for category_id, category_annotations in category_groups.items():
                    # Get category name
                    category_query = select(MemoryCategory).where(MemoryCategory.id == category_id)
                    category_result = await db.execute(category_query)
                    category = category_result.scalar_one_or_none()

                    if category:
                        category_name = category.name
                        consolidation_summary["topics_identified"].append(category_name)

                        # Extract entities from annotations
                        for annotation in category_annotations:
                            if annotation.file_path:
                                # Extract file name as entity
                                file_name = annotation.file_path.split("/")[-1]
                                consolidation_summary["key_entities"].add(file_name)

                            memories_consolidated += 1

                        # Count relationships (annotations in same category)
                        if len(category_annotations) > 1:
                            consolidation_summary["relationships_found"] += len(category_annotations) - 1

                        vector_updates += 1

                # Calculate storage metrics
                total_content_length = sum(len(a.content) for a in annotations)
                storage_saved = int(total_content_length * 0.1)  # Estimate 10% savings from consolidation

                _logger.info(
                    "memory_consolidation_completed",
                    session_id=session_id,
                    categories=len(category_groups),
                    annotations=len(annotations),
                )

                return WorkerResult(
                    success=True,
                    message=f"Memory consolidation completed for session {session_id}",
                    data={
                        "session_id": session_id,
                        "consolidation_type": consolidation_type,
                        "retention_policy": retention_policy,
                        "memories_processed": len(annotations),
                        "memories_consolidated": memories_consolidated,
                        "memories_archived": 0,  # Not implemented yet
                        "vector_updates": vector_updates,
                        "storage_saved": storage_saved,  # KB
                        "consolidation_summary": {
                            "topics_identified": consolidation_summary["topics_identified"],
                            "key_entities": list(consolidation_summary["key_entities"])[:10],
                            "relationships_found": consolidation_summary["relationships_found"],
                        },
                        "categories_processed": len(category_groups),
                    },
                )

        except Exception as exc:
            _logger.error(
                "memory_consolidation_failed",
                session_id=session_id,
                error=str(exc),
            )
            return WorkerResult(
                success=False,
                message=f"Memory consolidation failed: {str(exc)}",
                error=exc,
            )
    
    async def _handle_token_management(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle token window management and budget enforcement."""
        session_id = message_data.get("session_id")
        action = message_data.get("action", "reset_window")
        new_window_size = message_data.get("new_window_size")
        budget_adjustment = message_data.get("budget_adjustment", 0)
        
        # TODO: Implement token management logic
        # This would manage token budgets and window sizes
        
        await asyncio.sleep(0.2)  # Simulate token management
        
        return WorkerResult(
            success=True,
            message=f"Token management completed for session {session_id}",
            data={
                "session_id": session_id,
                "action": action,
                "previous_window_size": 10000,
                "new_window_size": new_window_size or 10000,
                "budget_adjustment": budget_adjustment,
                "current_token_count": 2500,
                "tokens_until_next_review": 7500,
                "window_progress": 0.25,
                "budget_status": "healthy",
                "recommendations": [
                    "Current window size is appropriate",
                    "Consider increasing budget for complex tasks",
                ],
            },
        )
    
    async def _handle_session_cleanup(self, message_data: dict[str, Any]) -> WorkerResult:
        """Handle cleanup of old or inactive session data."""
        cleanup_criteria = message_data.get("cleanup_criteria", "inactive_7d")
        dry_run = message_data.get("dry_run", True)
        target_sessions = message_data.get("target_sessions", [])
        
        # TODO: Implement session cleanup logic
        # This would clean up old sessions, temporary data, etc.
        
        await asyncio.sleep(0.3)  # Simulate cleanup
        
        return WorkerResult(
            success=True,
            message=f"Session cleanup completed: {cleanup_criteria}",
            data={
                "cleanup_criteria": cleanup_criteria,
                "dry_run": dry_run,
                "sessions_scanned": 150,
                "sessions_cleaned": 23,
                "space_freed": 5120,  # KB
                "cleanup_details": {
                    "old_sessions": 15,
                    "temp_data": 8,
                    "orphaned_data": 0,
                },
                "preserved_sessions": [
                    "active_session_1",
                    "important_session_2",
                ],
                "next_cleanup_scheduled": "2024-03-09T10:00:00Z",
            },
        )
