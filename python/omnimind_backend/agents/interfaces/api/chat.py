"""Chat API interfaces.

Defines contracts for chat operations, streaming,
and real-time communication.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from omnimind_backend.schemas.chat.agent import AgentChatRequest, StreamEvent


@runtime_checkable
class ChatInterface(Protocol):
    """Contract for chat API implementations."""
    
    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response."""
        ...

    async def get_session_history(self, session_id: str) -> list[dict]:
        """Get chat session history."""
        ...

    async def create_session(self, title: str | None = None) -> str:
        """Create new chat session."""
        ...
