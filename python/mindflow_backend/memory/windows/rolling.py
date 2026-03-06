"""Rolling window operations for memory."""

from typing import Any, Dict, List, Optional

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.database import MemoryDatabase
from mindflow_backend.memory.storage.models import AgentMemoryCursor, AgentMemoryEvent

_logger = get_logger(__name__)


class RollingWindow:
    """Rolling memory window management."""
    
    def __init__(self, window_size: int = 4000):
        self.window_size = window_size
        self.memory_db = MemoryDatabase()
        self.logger = _logger
    
    def should_create_window(
        self,
        cursor: AgentMemoryCursor,
        new_tokens: int
    ) -> bool:
        """Check if should create a new memory window."""
        return cursor.tokens_since_summary + new_tokens >= self.window_size
    
    def get_window_events(
        self,
        session_id: str,
        agent_id: str,
        cursor: AgentMemoryCursor
    ) -> List[AgentMemoryEvent]:
        """Get events for the current window."""
        try:
            with self.memory_db.get_db_session() as db:
                start_event_id = (cursor.last_summarized_event_id or 0) + 1
                
                events = list(db.scalars(
                    select(AgentMemoryEvent).where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                        AgentMemoryEvent.id >= start_event_id
                    ).order_by(AgentMemoryEvent.id.asc())
                ))
                
                return events
                
        except Exception as exc:
            self.logger.error(f"Failed to get window events: {str(exc)}")
            return []
    
    def calculate_window_stats(
        self,
        events: List[AgentMemoryEvent]
    ) -> Dict[str, Any]:
        """Calculate statistics for the window."""
        if not events:
            return {
                "event_count": 0,
                "total_tokens": 0,
                "roles": {},
                "time_span": None
            }
        
        total_tokens = sum(event.token_count for event in events)
        role_counts = {}
        
        for event in events:
            role_counts[event.role] = role_counts.get(event.role, 0) + 1
        
        time_span = {
            "start": events[0].created_at.isoformat(),
            "end": events[-1].created_at.isoformat()
        } if len(events) > 1 else None
        
        return {
            "event_count": len(events),
            "total_tokens": total_tokens,
            "roles": role_counts,
            "time_span": time_span
        }
