"""
AgentRuntime - Main runtime orchestrator for MindFlow agents.

This module is the refactored version of the monolithic AgentRuntime,
split into focused modules for better maintainability.
"""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Optional

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent, StreamEventMeta

_logger = get_logger(__name__)

# Lazy imports for optional services
_get_memory_service = None
_get_execution_memory_service = None
langgraph_memory = None
_RabbitMQMemoryTaskPublisher = None
db_session = None
ChatMessage = None
ChatSession = None

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception:
    pass

try:
    from mindflow_backend.execution_memory import (
        get_execution_memory_service as _get_execution_memory_service,
    )
except Exception:
    pass

try:
    from mindflow_backend.memory.agent_memory.checkpointer import langgraph_memory
except Exception:
    pass

try:
    from mindflow_backend.workers.system.publishers.memory_publisher import (
        RabbitMQMemoryTaskPublisher as _RabbitMQMemoryTaskPublisher,
    )
except Exception:
    pass

try:
    from mindflow_backend.infra.database.connection import get_db_session as db_session
    from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession
except Exception:
    pass


class AgentRuntime:
    """
    Main runtime orchestrator for MindFlow agents.
    
    Coordinates streaming, routing, execution, and memory integration.
    Delegates specialized operations to focused modules.
    """
    
    def __init__(self) -> None:
        self._orchestrator_graph = None
        self._memory_service = _get_memory_service() if _get_memory_service else None
        self._execution_memory = _get_execution_memory_service() if _get_execution_memory_service else None
        self._memory_publisher = _RabbitMQMemoryTaskPublisher() if _RabbitMQMemoryTaskPublisher else None
        
        # Import specialized modules
        from ..routing.runtime_router import RuntimeRouter
        from ..execution.executor import RuntimeExecutor
        from ..streaming.stream_manager import StreamManager
        from ..memory.memory_integration import MemoryIntegration
        
        self._router = RuntimeRouter()
        self._executor = RuntimeExecutor()
        self._stream_manager = StreamManager()
        self._memory = MemoryIntegration(
            memory_service=self._memory_service,
            execution_memory=self._execution_memory,
            memory_publisher=self._memory_publisher,
        )
    
    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Main entry point for streaming chat responses.
        
        Routes to orchestrated, direct agent, or legacy execution
        based on the request payload.
        """
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        run_id = run_id or str(uuid.uuid4())
        counter = [0]
        memory_agent_id = self._memory.resolve_memory_agent_id(payload)
        
        execution = await self._memory.start_execution(
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            provider=provider,
            model=model,
        )
        execution_id = getattr(execution, "id", None)
        
        # Save user message in background
        asyncio.create_task(
            self._memory.save_message_bg(
                session_id=session_id,
                role="user",
                content=payload.message,
                memory_agent_id=memory_agent_id,
            )
        )
        
        assistant_content = []
        assistant_completed = False
        
        try:
            if execution_id:
                yield self._stream_manager.custom_event(
                    counter=counter,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="agent_execution_start",
                    data=json.dumps({"execution_id": execution_id}),
                    agent="orchestrator" if payload.orchestrate else getattr(payload, "agent_type", None),
                )
            
            execution_mode = self._router.resolve_execution_mode(payload)
            
            if execution_mode == "orchestrated":
                async for event in self._executor.stream_orchestrated(
                    payload, session_id, run_id, execution_id=execution_id
                ):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event
            
            elif execution_mode == "direct":
                async for event in self._executor.stream_direct_agent(
                    payload, session_id, run_id, execution_id=execution_id
                ):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event
            
            else:
                async for event in self._executor.stream_legacy(
                    payload, session_id, run_id
                ):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event
            
            # Mark execution as completed
            await self._memory.complete_execution(execution_id, session_id)
        
        finally:
            # Save assistant response
            full_response = "".join(assistant_content)
            if full_response:
                asyncio.create_task(
                    self._memory.save_message_bg(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        memory_agent_id=memory_agent_id,
                        provider=provider,
                        model=model,
                        source_status="final" if assistant_completed else "partial",
                    )
                )
    
    async def create_execution(
        self,
        payload: AgentChatRequest,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new execution record."""
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        resolved_session_id = session_id or payload.sessionId or f"sess-{uuid.uuid4()}"
        
        execution = await self._memory.start_execution(
            payload=payload,
            session_id=resolved_session_id,
            run_id=run_id,
            provider=provider,
            model=model,
            execution_id=getattr(payload, "execution_id", None),
            status="queued",
        )
        
        if execution is None:
            raise RuntimeError("Execution memory service is unavailable.")
        
        return await self.get_execution_status(execution.id)
    
    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Get execution status and details."""
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")
        
        execution = await self._execution_memory.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")
        
        return {
            "execution_id": execution_id,
            "status": getattr(execution, "status", "unknown"),
            "stage": getattr(execution, "current_stage", None),
            "metadata": getattr(execution, "metadata", {}),
        }
    
    async def pause_execution(self, execution_id: str, *, reason: str | None = None) -> dict[str, Any]:
        """Pause an execution."""
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")
        
        await self._execution_memory.request_pause(execution_id=execution_id, reason=reason)
        return await self.get_execution_status(execution_id)