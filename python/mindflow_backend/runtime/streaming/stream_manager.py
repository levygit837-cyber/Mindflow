"""
Stream Manager - Handles stream event creation and normalization.

Provides utilities for creating typed stream events.
"""

import uuid

from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta


class StreamManager:
    """
    Manages stream event creation and formatting.
    
    Provides consistent event creation across all execution modes.
    """
    
    @staticmethod
    def next_seq(counter: list[int]) -> int:
        """Increment and return the mutable sequence counter."""
        counter[0] += 1
        return counter[0]
    
    @staticmethod
    def create_context(
        provider: str,
        model: str,
        session_id: str,
        run_id: str | None = None,
    ) -> tuple[str, str, str, AgentChatStreamNormalizer, list[int]]:
        """Create stream context with normalizer and counter."""
        run_id = run_id or str(uuid.uuid4())
        normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)
        return provider, model, run_id, normalizer, [0]
    
    def error_event(
        self,
        *,
        exc: Exception,
        counter: list[int],
        provider: str,
        model: str,
        run_id: str,
        session_id: str,
        node: str,
        node_category: str,
    ) -> StreamEvent:
        """Build a typed error StreamEvent."""
        seq = self.next_seq(counter)
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="error",
            mode="custom",
            data=str(exc),
            meta=StreamEventMeta(
                provider=provider,
                model=model,
                runId=run_id,
                turnRunId=session_id,
                node=node,
                nodeCategory=node_category,
                userVisible=True,
            ),
        )
    
    def done_event(
        self,
        *,
        counter: list[int],
        provider: str,
        model: str,
        run_id: str,
        session_id: str,
    ) -> StreamEvent:
        """Build the terminal done StreamEvent."""
        seq = self.next_seq(counter)
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="done",
            mode="messages",
            data="",
            meta=StreamEventMeta(provider=provider, model=model, runId=run_id, turnRunId=session_id),
        )
    
    def custom_event(
        self,
        *,
        counter: list[int],
        run_id: str,
        session_id: str,
        event_type: str,
        data: str = "",
        agent: str | None = None,
    ) -> StreamEvent:
        """Build a custom stream event."""
        seq = self.next_seq(counter)
        meta = StreamEventMeta(
            runId=run_id,
            turnRunId=session_id,
            node="orchestrator",
            nodeCategory="RUNTIME",
            userVisible=True,
        )
        if agent:
            meta.agent = agent
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type=event_type,
            mode="custom",
            data=data,
            meta=meta,
        )