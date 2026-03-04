"""Streaming interface.

Defines the contract for real-time streaming, event handling,
and metadata management based on agent.py StreamEvent schemas.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable, Any

from omnimind_backend.schemas.chat.agent import (
    AgentChatRequest,
    AgentChatStreamPayload,
    StreamEvent,
    StreamEventMeta,
    StreamEventType,
    StreamModeName,
)


@runtime_checkable
class StreamingContract(Protocol):
    """Contract for streaming operations and event handling.
    
    Handles real-time streaming of agent responses, event
    processing, and metadata management.
    """

    async def stream_response(
        self,
        request: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream chat response for agent interaction.
        
        Args:
            request: Chat request from user.
            session_id: Session identifier.
            run_id: Optional run identifier.
            
        Yields:
            Stream events for real-time response.
        """
        ...

    async def handle_stream_event(
        self,
        event: StreamEvent,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Handle individual stream events.
        
        Args:
            event: Stream event to handle.
            context: Additional context for event handling.
        """
        ...

    async def create_stream_metadata(
        self,
        event_type: StreamEventType,
        mode: StreamModeName,
        run_id: str | None = None,
        parent_run_id: str | None = None,
        node: str | None = None,
        user_visible: bool = True,
    ) -> StreamEventMeta:
        """Create metadata for stream events.
        
        Args:
            event_type: Type of stream event.
            mode: Streaming mode.
            run_id: Run identifier.
            parent_run_id: Parent run identifier.
            node: Node identifier.
            user_visible: Whether event is user visible.
            
        Returns:
            Stream event metadata.
        """
        ...

    async def create_stream_event(
        self,
        event_id: str,
        sequence: int,
        event_type: StreamEventType,
        mode: StreamModeName,
        data: str,
        metadata: StreamEventMeta | None = None,
    ) -> StreamEvent:
        """Create a structured stream event.
        
        Args:
            event_id: Unique event identifier.
            sequence: Event sequence number.
            event_type: Type of stream event.
            mode: Streaming mode.
            data: Event data payload.
            metadata: Event metadata.
            
        Returns:
            Structured stream event.
        """
        ...

    async def process_stream_payload(
        self,
        payload: AgentChatStreamPayload,
    ) -> dict[str, Any]:
        """Process internal stream payload.
        
        Args:
            payload: Internal stream payload from runtime.
            
        Returns:
            Processed payload data.
        """
        ...

    async def filter_events(
        self,
        events: AsyncGenerator[StreamEvent, None],
        event_types: list[StreamEventType] | None = None,
        user_visible_only: bool = False,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Filter stream events based on criteria.
        
        Args:
            events: Stream of events to filter.
            event_types: Event types to include.
            user_visible_only: Only include user visible events.
            
        Yields:
            Filtered stream events.
        """
        ...

    async def aggregate_events(
        self,
        events: list[StreamEvent],
        aggregation_window: float = 1.0,
    ) -> dict[str, Any]:
        """Aggregate stream events over time window.
        
        Args:
            events: List of events to aggregate.
            aggregation_window: Time window for aggregation.
            
        Returns:
            Aggregated event data.
        """
        ...

    async def create_thought_event(
        self,
        thought_data: str,
        run_id: str | None = None,
        node: str | None = None,
    ) -> StreamEvent:
        """Create a thought stream event.
        
        Args:
            thought_data: Thought content.
            run_id: Run identifier.
            node: Node identifier.
            
        Returns:
            Thought stream event.
        """
        ...

    async def create_tool_call_event(
        self,
        tool_call_data: dict[str, Any],
        run_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> StreamEvent:
        """Create a tool call stream event.
        
        Args:
            tool_call_data: Tool call information.
            run_id: Run identifier.
            tool_call_id: Tool call identifier.
            
        Returns:
            Tool call stream event.
        """
        ...

    async def create_response_event(
        self,
        response_data: str,
        run_id: str | None = None,
        user_visible: bool = True,
    ) -> StreamEvent:
        """Create a response stream event.
        
        Args:
            response_data: Response content.
            run_id: Run identifier.
            user_visible: Whether response is user visible.
            
        Returns:
            Response stream event.
        """
        ...

    async def create_error_event(
        self,
        error_data: str,
        run_id: str | None = None,
        node: str | None = None,
    ) -> StreamEvent:
        """Create an error stream event.
        
        Args:
            error_data: Error information.
            run_id: Run identifier.
            node: Node identifier.
            
        Returns:
            Error stream event.
        """
        ...

    async def create_done_event(
        self,
        final_data: str = "",
        run_id: str | None = None,
    ) -> StreamEvent:
        """Create a completion stream event.
        
        Args:
            final_data: Final data payload.
            run_id: Run identifier.
            
        Returns:
            Completion stream event.
        """
        ...

    async def validate_stream_event(
        self,
        event: StreamEvent,
    ) -> bool:
        """Validate stream event structure and content.
        
        Args:
            event: Stream event to validate.
            
        Returns:
            True if event is valid.
        """
        ...

    async def get_stream_statistics(
        self,
        session_id: str,
        time_window: str = "1h",
    ) -> dict[str, Any]:
        """Get streaming statistics for a session.
        
        Args:
            session_id: Session identifier.
            time_window: Time window for statistics.
            
        Returns:
            Streaming statistics and metrics.
        """
        ...
