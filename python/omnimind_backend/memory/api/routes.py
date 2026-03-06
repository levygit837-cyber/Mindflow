"""Memory API endpoints."""

from fastapi import APIRouter

from omnimind_backend.api.controllers.memory_controller import MemoryController
from omnimind_backend.api.schemas.requests import (
    MemorySearchRequest,
    MemorySummaryRequest,
    ContextWindowRequest
)

router = APIRouter(prefix="/memory", tags=["memory"])

# Initialize controller
memory_controller = MemoryController()


@router.get("/agents/{agent_id}/sessions/{session_id}")
async def get_agent_memory(
    agent_id: str,
    session_id: str,
    token_limit: int | None = None
):
    """Get memory for a specific agent in a session."""
    return await memory_controller.get_agent_memory(agent_id, session_id, token_limit)


@router.post("/search")
async def search_memory(request: MemorySearchRequest):
    """Search memory/context using semantic similarity."""
    return await memory_controller.search_memory(request)


@router.post("/agents/{agent_id}/sessions/{session_id}/events")
async def add_memory_event(
    agent_id: str,
    session_id: str,
    role: str,
    content: str,
    token_count: int,
    source_message_id: int | None = None
):
    """Add a memory event for an agent."""
    return await memory_controller.add_memory_event(
        agent_id, session_id, role, content, token_count, source_message_id
    )


@router.get("/sessions/{session_id}/context")
async def get_context_window(
    session_id: str,
    window_start: int,
    window_end: int
):
    """Get a specific context window."""
    return await memory_controller.get_context_window(session_id, window_start, window_end)


@router.post("/agents/{agent_id}/sessions/{session_id}/summary")
async def create_memory_summary(
    agent_id: str,
    session_id: str,
    window_start: int,
    window_end: int,
    summary_type: str = "auto"
):
    """Create a summary of a memory window."""
    return await memory_controller.create_memory_summary(
        agent_id, session_id, window_start, window_end, summary_type
    )


@router.get("/agents/{agent_id}/sessions/{session_id}/windows")
async def get_memory_windows(agent_id: str, session_id: str):
    """Get all memory windows for an agent."""
    return await memory_controller.get_memory_windows(agent_id, session_id)


@router.put("/agents/{agent_id}/sessions/{session_id}/cursor")
async def update_memory_cursor(
    agent_id: str,
    session_id: str,
    token_total: int,
    tokens_since_summary: int
):
    """Update memory cursor for an agent."""
    return await memory_controller.update_memory_cursor(
        agent_id, session_id, token_total, tokens_since_summary
    )


@router.get("/sessions/{session_id}/stats")
async def get_session_memory_stats(session_id: str):
    """Get memory statistics for a session."""
    return await memory_controller.get_session_memory_stats(session_id)


@router.post("/sessions/{session_id}/cleanup")
async def cleanup_old_memory(
    session_id: str,
    days_to_keep: int = 30
):
    """Clean up old memory data for a session."""
    return await memory_controller.cleanup_old_memory(session_id, days_to_keep)
