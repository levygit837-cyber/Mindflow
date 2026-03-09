"""Context retrieval operations for memory."""

from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.database import MemoryDatabase
from mindflow_backend.memory.storage.models import AgentMemoryEvent, AgentMemoryWindow

_logger = get_logger(__name__)


class ContextRetriever:
    """Context retrieval and assembly for memory."""
    
    def __init__(self):
        self.memory_db = MemoryDatabase()
        self.logger = _logger
    
    def get_recent_context(
        self,
        session_id: str,
        agent_id: str,
        token_limit: int = 2000
    ) -> Dict[str, Any]:
        """Get recent context within token limit."""
        try:
            with self.memory_db.get_db_session() as db:
                # Get recent events
                events = self.memory_db.get_memory_events(
                    db, session_id, agent_id, limit=50
                )
                
                # Accumulate events until token limit reached
                context_events = []
                total_tokens = 0
                
                for event in events:
                    if total_tokens + event.token_count > token_limit:
                        break
                    context_events.append(event)
                    total_tokens += event.token_count
                
                # Format context
                context_parts = []
                for event in context_events:
                    context_parts.append(f"[{event.role}]: {event.content}")
                
                context = "\n\n".join(context_parts)
                
                return {
                    "context": context,
                    "events": [
                        {
                            "id": event.id,
                            "role": event.role,
                            "content": event.content,
                            "token_count": event.token_count,
                            "created_at": event.created_at.isoformat()
                        }
                        for event in context_events
                    ],
                    "total_tokens": total_tokens,
                    "event_count": len(context_events),
                    "retrieval_method": "recent_context"
                }
                
        except Exception as exc:
            self.logger.error(f"Failed to get recent context: {str(exc)}")
            return {"context": "", "events": [], "total_tokens": 0, "event_count": 0}
    
    def get_window_context(
        self,
        session_id: str,
        agent_id: str,
        window_count: int = 3
    ) -> Dict[str, Any]:
        """Get context from memory windows."""
        try:
            with self.memory_db.get_db_session() as db:
                windows = self.memory_db.get_memory_windows(
                    db, session_id, agent_id
                )
                
                # Take the most recent windows
                recent_windows = windows[:window_count]
                
                context_parts = []
                for window in recent_windows:
                    context_parts.append(f"[window:{window.window_index}] {window.summary_md}")
                
                context = "\n\n".join(context_parts)
                
                return {
                    "context": context,
                    "windows": [
                        {
                            "id": window.id,
                            "window_index": window.window_index,
                            "summary": window.summary_md,
                            "key_points": window.key_points,
                            "token_range": [window.token_start, window.token_end],
                            "created_at": window.created_at.isoformat()
                        }
                        for window in recent_windows
                    ],
                    "window_count": len(recent_windows),
                    "retrieval_method": "window_context"
                }
                
        except Exception as exc:
            self.logger.error(f"Failed to get window context: {str(exc)}")
            return {"context": "", "windows": [], "window_count": 0}
    
    def get_hybrid_context(
        self,
        session_id: str,
        agent_id: str,
        query: str,
        recent_token_limit: int = 1000,
        window_count: int = 2
    ) -> Dict[str, Any]:
        """Get hybrid context combining recent events and windows."""
        try:
            # Get recent context
            recent_context = self.get_recent_context(
                session_id, agent_id, recent_token_limit
            )
            
            # Get window context
            window_context = self.get_window_context(
                session_id, agent_id, window_count
            )
            
            # Combine contexts
            combined_parts = []
            
            if recent_context["context"]:
                combined_parts.append("## Recent Context")
                combined_parts.append(recent_context["context"])
            
            if window_context["context"]:
                combined_parts.append("## Memory Windows")
                combined_parts.append(window_context["context"])
            
            combined_context = "\n\n".join(combined_parts)
            
            return {
                "context": combined_context,
                "recent": recent_context,
                "windows": window_context,
                "query": query,
                "retrieval_method": "hybrid_context"
            }
            
        except Exception as exc:
            self.logger.error(f"Failed to get hybrid context: {str(exc)}")
            return {"context": "", "recent": {}, "windows": {}, "query": query}
    
    def format_context_for_query(
        self,
        query: str,
        context_items: List[Dict[str, Any]]
    ) -> str:
        """Format context items for query response."""
        context_parts = [f"Context for query: {query}"]
        
        for item in context_items:
            content = item.get("content", "")
            source = item.get("source", "unknown")
            score = item.get("score", 0.0)
            
            if content:
                context_parts.append(f"- [{source}] (score: {score:.3f}): {content}")
        
        return "\n\n".join(context_parts)
