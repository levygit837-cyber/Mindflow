"""Memory database operations."""

from contextlib import contextmanager

from sqlalchemy import select
from sqlalchemy.orm import Session

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.storage.models import AgentMemoryEvent, AgentMemoryWindow

_logger = get_logger(__name__)


class MemoryDatabase:
    """Database operations for memory management."""

    def __init__(self) -> None:
        self.logger = _logger

    @contextmanager
    def get_db_session(self):
        from mindflow_backend.infra.database.connection import get_db_session
        with get_db_session() as db:
            yield db

    def get_memory_events(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
        limit: int | None = None,
    ) -> list[AgentMemoryEvent]:
        query = (
            select(AgentMemoryEvent)
            .where(
                AgentMemoryEvent.session_id == session_id,
                AgentMemoryEvent.agent_id == agent_id,
            )
            .order_by(AgentMemoryEvent.created_at.desc())
        )
        if limit:
            query = query.limit(limit)
        return list(db.execute(query).scalars())

    def get_memory_windows(
        self,
        db: Session,
        session_id: str,
        agent_id: str,
    ) -> list[AgentMemoryWindow]:
        query = (
            select(AgentMemoryWindow)
            .where(
                AgentMemoryWindow.session_id == session_id,
                AgentMemoryWindow.agent_id == agent_id,
            )
            .order_by(AgentMemoryWindow.window_start.desc())
        )
        return list(db.execute(query).scalars())
