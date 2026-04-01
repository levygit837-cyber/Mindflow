"""
Stream Manager - Handles stream event creation and normalization.

Provides utilities for creating typed stream events.
"""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.schemas.chat.agent import StreamEvent, StreamEventMeta

_logger = get_logger(__name__)


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

    async def stream_tool_execution(
        self,
        executor: Any,  # StreamingToolExecutor
        *,
        counter: list[int],
        provider: str,
        model: str,
        run_id: str,
        session_id: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream de execução de ferramentas.

        Emite eventos:
        - tool_start: Quando ferramenta inicia
        - tool_result: Quando ferramenta completa
        - tool_error: Quando ferramenta falha

        Args:
            executor: StreamingToolExecutor com ferramentas adicionadas
            counter: Contador de sequência
            provider: Provedor do modelo
            model: Modelo sendo usado
            run_id: ID da execução
            session_id: ID da sessão
        """
        normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)

        try:
            async for streaming_result in executor.get_remaining_results():
                if streaming_result.status.value == "running":
                    # Emite tool_start
                    yield normalizer.tool_call_event(
                        self.next_seq(counter),
                        tool_call_id=streaming_result.tool_id,
                        name=streaming_result.tool_name,
                        args={},
                        run_id=run_id,
                    )

                elif streaming_result.status.value == "completed" and streaming_result.result:
                    # Emite tool_result
                    result_data = streaming_result.result.to_dict() if hasattr(streaming_result.result, 'to_dict') else str(streaming_result.result)
                    yield normalizer.tool_result_event(
                        self.next_seq(counter),
                        tool_call_id=streaming_result.tool_id,
                        name=streaming_result.tool_name,
                        result=json.dumps(result_data) if isinstance(result_data, dict) else str(result_data),
                        run_id=run_id,
                    )

                elif streaming_result.status.value == "error":
                    # Emite tool_error
                    yield self.error_event(
                        exc=Exception(streaming_result.error or "Unknown error"),
                        counter=counter,
                        provider=provider,
                        model=model,
                        run_id=run_id,
                        session_id=session_id,
                        node="streaming_executor",
                        node_category="TOOL_EXECUTION",
                    )

                elif streaming_result.status.value == "discarded":
                    # Log discarded
                    _logger.info(
                        "tool_discarded",
                        tool_id=streaming_result.tool_id,
                        tool_name=streaming_result.tool_name,
                    )

        except Exception as exc:
            _logger.error("stream_tool_execution_error", error=str(exc))
            yield self.error_event(
                exc=exc,
                counter=counter,
                provider=provider,
                model=model,
                run_id=run_id,
                session_id=session_id,
                node="streaming_executor",
                node_category="TOOL_EXECUTION",
            )

        # Emite evento done
        yield self.done_event(
            counter=counter,
            provider=provider,
            model=model,
            run_id=run_id,
            session_id=session_id,
        )
