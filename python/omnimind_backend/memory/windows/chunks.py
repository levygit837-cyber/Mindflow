"""Session chunk processing for memory."""

import re
from typing import Any, Dict, List, Optional

from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.storage.models import AgentMemoryEvent, SessionChunk
from omnimind_backend.llm.providers import get_model_for_provider

_logger = get_logger(__name__)


class ChunkProcessor:
    """Session chunk processing and analysis."""
    
    def __init__(self):
        self.logger = _logger
    
    async def process_chunk(
        self,
        events: List[AgentMemoryEvent],
        session_id: str,
        agent_id: str,
        sequence: int
    ) -> SessionChunk:
        """Process a chunk of events using LLM analysis."""
        try:
            # Concatenate event content
            event_content = "\n".join(f"[{event.role}]: {event.content}" for event in events)
            
            # Get LLM for analysis
            settings = get_settings()
            llm = get_model_for_provider(settings.default_provider, settings.default_model)
            
            # Use analyst critic sub-personality for chunk analysis
            from omnimind_backend.agents.core.personalities import ANALYST_SUB_PERSONALITIES
            critic_prompt = ANALYST_SUB_PERSONALITIES.get("critic", "")
            
            analysis_prompt = f"""{critic_prompt}

Analyze the following conversation chunk and provide a structured summary:

CONVERSATION CHUNK:
{event_content}

Provide your analysis in this exact format:
SUMMARY: [brief summary of the chunk content]
CHUNK_TYPE: [discussion|question_answer|planning|decision|other]
TOPIC_TAGS: [tag1,tag2,tag3]
CONFIDENCE: [0.0-1.0 confidence score]

Focus on extracting the main topics, conversation type, and key themes."""
            
            response = llm.invoke(analysis_prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse response with regex
            summary_match = re.search(r'SUMMARY:\s*(.+?)(?=\nCHUNK_TYPE:|$)', response_text, re.DOTALL)
            chunk_type_match = re.search(r'CHUNK_TYPE:\s*(.+?)(?=\nTOPIC_TAGS:|$)', response_text, re.DOTALL)
            tags_match = re.search(r'TOPIC_TAGS:\s*(.+?)(?=\nCONFIDENCE:|$)', response_text, re.DOTALL)
            confidence_match = re.search(r'CONFIDENCE:\s*([0-9.]+)', response_text)
            
            # Extract values with fallbacks
            content_summary = summary_match.group(1).strip() if summary_match else event_content[:500] + "..."
            chunk_type_raw = chunk_type_match.group(1).strip().lower() if chunk_type_match else "discussion"
            tags_raw = tags_match.group(1).strip() if tags_match else ""
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Validate chunk type
            valid_types = {"discussion", "question_answer", "planning", "decision", "other"}
            chunk_type = chunk_type_raw if chunk_type_raw in valid_types else "discussion"
            
            # Parse tags
            topic_tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []
            
            # Create session chunk
            chunk = SessionChunk(
                session_id=session_id,
                agent_id=agent_id,
                sequence=sequence,
                chunk_type=chunk_type,
                content_summary=content_summary,
                topic_tags=topic_tags,
                token_count=sum(event.token_count for event in events),
                event_start_id=events[0].id if events else 0,
                event_end_id=events[-1].id if events else 0,
                confidence=confidence,
            )
            
            self.logger.info(
                "session_chunk_processed",
                session_id=session_id,
                agent_id=agent_id,
                chunk_sequence=sequence,
                chunk_type=chunk_type,
                token_count=chunk.token_count,
            )
            
            return chunk
            
        except Exception as exc:
            self.logger.error(
                "session_chunk_processing_failed",
                session_id=session_id,
                agent_id=agent_id,
                error=str(exc),
                exc_info=True,
            )
            # Return fallback chunk
            return SessionChunk(
                session_id=session_id,
                agent_id=agent_id,
                sequence=sequence,
                chunk_type="other",
                content_summary="Chunk processing failed",
                topic_tags=[],
                token_count=sum(event.token_count for event in events),
                event_start_id=events[0].id if events else 0,
                event_end_id=events[-1].id if events else 0,
                confidence=0.0,
            )
    
    def should_create_chunk(
        self,
        cursor_tokens_since_chunk: int,
        target_tokens: Optional[int] = None
    ) -> bool:
        """Check if should create a new chunk."""
        if target_tokens is None:
            target_tokens = get_settings().chunk_target_tokens or 2000
        
        return cursor_tokens_since_chunk >= target_tokens
    
    def get_chunk_statistics(
        self,
        chunks: List[SessionChunk]
    ) -> Dict[str, Any]:
        """Get statistics for chunks."""
        if not chunks:
            return {
                "total_chunks": 0,
                "chunk_types": {},
                "average_confidence": 0.0,
                "total_tokens": 0
            }
        
        chunk_types = {}
        total_confidence = 0.0
        total_tokens = 0
        
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            total_confidence += chunk.confidence
            total_tokens += chunk.token_count
        
        return {
            "total_chunks": len(chunks),
            "chunk_types": chunk_types,
            "average_confidence": total_confidence / len(chunks),
            "total_tokens": total_tokens
        }
