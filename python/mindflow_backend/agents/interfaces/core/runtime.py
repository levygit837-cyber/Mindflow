"""Runtime interfaces.

Defines contracts for agent runtime operations, factory patterns,
content analysis, and result parsing.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any, Protocol, runtime_checkable

from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent
from mindflow_backend.schemas.session.review import ReviewExecutionContext


@runtime_checkable
class AgentRuntime(Protocol):
    """Contract for agent runtime implementations."""
    
    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response for agent interaction."""
        ...


@runtime_checkable
class AgentFactory(Protocol):
    """Contract for agent factory implementations."""
    
    def create_agent(self, agent_type: str, config: dict) -> Any:
        """Create an agent instance of the specified type."""
        ...

    def get_available_agents(self) -> list[str]:
        """Get list of available agent types."""
        ...

    def register_agent(self, agent_type: str, factory: Callable) -> None:
        """Register a new agent type factory."""
        ...


@runtime_checkable
class ContentAnalyzer(Protocol):
    """Contract for content analysis implementations."""
    
    async def analyze_window(
        self,
        context: ReviewExecutionContext,
    ) -> str:
        """Analyze session window and extract insights."""
        ...


@runtime_checkable
class ResultParser(Protocol):
    """Contract for result parsing implementations."""
    
    def parse_actions(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Parse actions from analysis content."""
        ...

    def parse_insights(
        self,
        analysis_content: str,
        session_id: str,
        window_range: tuple[int, int],
    ) -> list[dict[str, Any]]:
        """Parse insights from analysis content."""
        ...
