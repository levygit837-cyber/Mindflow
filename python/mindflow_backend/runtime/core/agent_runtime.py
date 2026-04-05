"""
AgentRuntime - Main runtime orchestrator for MindFlow agents.

This module is the refactored version of the monolithic AgentRuntime,
split into focused modules for better maintainability.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent

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
    pass
except Exception:
    pass

try:
    from mindflow_backend.workers.system.publishers.memory_publisher import (
        RabbitMQMemoryTaskPublisher as _RabbitMQMemoryTaskPublisher,
    )
except Exception:
    pass

try:
    pass
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
        from ..execution.executor import RuntimeExecutor
        from ..memory.memory_integration import MemoryIntegration
        from ..routing.runtime_router import RuntimeRouter
        from ..streaming.stream_manager import StreamManager

        self._router = RuntimeRouter()
        self._executor = RuntimeExecutor()
        self._stream_manager = StreamManager()
        self._memory = MemoryIntegration(
            memory_service=self._memory_service,
            execution_memory=self._execution_memory,
            memory_publisher=self._memory_publisher,
        )

        # Initialize unified QueryEngine for direct execution (lazy import to avoid circular dependency)
        self._query_engine: Any = None

        # Initialize CommunicationBus and register agents
        asyncio.create_task(self._initialize_communication_bus())

    def _get_query_engine(self, session_id: str) -> Any:
        """Get or create the QueryEngine for this session (lazy import to avoid circular dependency)."""
        if self._query_engine is None:
            from mindflow_backend.query.budget.token_counter import TokenBudget
            from mindflow_backend.query.engine import QueryEngine

            self._query_engine = QueryEngine(
                providers=[],  # No context providers for runtime execution
                budget=TokenBudget(max_tokens=200_000),
                system_prompt="",  # Use agent-specific prompts
                session_id=session_id,
                use_file_cache=True,
                execution_memory=self._execution_memory,
            )
        return self._query_engine
    
    async def _initialize_communication_bus(self) -> None:
        """Initialize CommunicationBus (Internal or XMPP based on feature flag) and register agents."""
        try:
            settings = get_settings()

            if settings.use_xmpp_transport:
                from mindflow_backend.communication.bus import (
                    XMPPCommunicationBus,
                    get_communication_bus,
                    set_communication_bus,
                )
                from mindflow_backend.communication.connection.xmpp_connection import (
                    XMPPConnectionConfig,
                )

                config = XMPPConnectionConfig(
                    server=settings.xmpp_server,
                    port=settings.xmpp_port,
                    domain=settings.xmpp_domain,
                    use_tls=settings.xmpp_use_tls,
                )
                xmpp_bus = XMPPCommunicationBus(config)
                connected = await xmpp_bus.connect()

                if connected:
                    set_communication_bus(xmpp_bus)
                    _logger.info(
                        "xmpp_transport_activated",
                        extra={
                            "server": settings.xmpp_server,
                            "domain": settings.xmpp_domain,
                        },
                    )
                else:
                    _logger.warning(
                        "xmpp_transport_failed_fallback_to_internal",
                        extra={"server": settings.xmpp_server},
                    )
            else:
                # InternalBus is already default (lazy init via get_communication_bus)
                _logger.info("internal_bus_transport_default")

            # Register agents (works for both InternalBus and XMPPBus)
            from mindflow_backend.agents.specialists.runtime_policy import (
                list_agent_runtime_policies,
            )
            from mindflow_backend.communication.bus import get_communication_bus

            bus = get_communication_bus()
            for policy in list_agent_runtime_policies():
                await bus.register_agent(policy.agent_id)
            _logger.info(
                "communication_bus_agents_registered",
                extra={
                    "count": len(list_agent_runtime_policies()),
                    "bus_type": type(bus).__name__,
                },
            )
        except Exception as exc:
            _logger.warning(
                "communication_bus_init_failed",
                extra={"error": str(exc)},
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

    # ─── Session Lifecycle Hooks ──────────────────────────────────

    async def start_session(self, session_id: str) -> None:
        """Start session with SessionStart + InstructionsLoaded hooks.

        Executed when a new session is initialized. Fires SessionStart hooks
        so other systems can react (logging, initialization, external services).
        """
        from mindflow_backend.hooks.handlers.session_start import SessionStartHandler

        try:
            async for result in SessionStartHandler.execute(session_id=session_id):
                if result.add_context:
                    _logger.debug(
                        "session_start_hook_context",
                        session_id=session_id,
                        context=result.add_context[:200],
                    )
        except Exception as exc:
            _logger.warning(
                "session_start_hooks_error",
                session_id=session_id,
                error=str(exc),
            )

    async def end_session(self, session_id: str, reason: str = "other") -> None:
        """End session with SessionEnd hooks.

        Executed when a session is terminated. Fires SessionEnd hooks
        so other systems can react (cleanup, logging, persistence).

        Args:
            session_id: The session ID to end
            reason: Why the session ended ("clear", "resume", "logout", "other")
        """
        from mindflow_backend.hooks.handlers.session_end import SessionEndHandler

        try:
            async for result in SessionEndHandler.execute(
                session_id=session_id,
                reason=reason,
            ):
                if result.add_context:
                    _logger.debug(
                        "session_end_hook_context",
                        session_id=session_id,
                        reason=reason,
                        context=result.add_context[:200],
                    )
        except Exception as exc:
            _logger.warning(
                "session_end_hooks_error",
                session_id=session_id,
                reason=reason,
                error=str(exc),
            )

    async def handle_user_prompt(self, session_id: str, prompt: str) -> None:
        """Process user prompt with UserPromptSubmit hooks.

        Executed when user submits a prompt. Fires UserPromptSubmit hooks
        so other systems can react (validation, enrichment, filtering).

        Args:
            session_id: The session ID
            prompt: The user's prompt text
        """
        from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler

        try:
            async for result in UserPromptSubmitHandler.execute(
                session_id=session_id,
                cwd=get_settings().working_path,
            ):
                if result.add_context:
                    _logger.debug(
                        "user_prompt_submit_hook_context",
                        session_id=session_id,
                        context=result.add_context[:200],
                    )
        except Exception as exc:
            _logger.warning(
                "user_prompt_submit_hooks_error",
                session_id=session_id,
                error=str(exc),
            )
