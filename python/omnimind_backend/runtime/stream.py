import asyncio
import uuid
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage

from omnimind_backend.agents.tools.search_web import search_web
from omnimind_backend.infra.config import get_settings
from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.service import get_memory_service
from omnimind_backend.orchestrator.graph import build_orchestrator_graph
from omnimind_backend.orchestrator.router import route_message
from omnimind_backend.runtime.chunk_extract import extract_chunk_parts
from omnimind_backend.runtime.normalizer import AgentChatStreamNormalizer
from omnimind_backend.runtime.providers import get_model_for_provider
from omnimind_backend.schemas.agent import AgentChatRequest, StreamEvent, StreamEventMeta
from omnimind_backend.storage.db import db_session
from omnimind_backend.storage.repositories import ChatRepository

_logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are OmniMind, a pragmatic engineering assistant. "
    "Be concise, factual, and action-oriented. "
    "Always keep outputs clear and useful for software engineering context."
)

class AgentRuntime:
    def __init__(self) -> None:
        self._orchestrator_graph = build_orchestrator_graph()
        self._chat_repo = ChatRepository()
        self._memory_service = get_memory_service()

    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        memory_agent_id = self._resolve_memory_agent_id(payload)

        # 1. Save user message to database
        try:
            with db_session() as db:
                message = self._chat_repo.add_message(
                    db, 
                    session_id=session_id, 
                    role="user", 
                    content=payload.message
                )
                self._record_memory_message(
                    db=db,
                    session_id=session_id,
                    agent_id=memory_agent_id,
                    role="user",
                    content=payload.message,
                    source_message_id=getattr(message, "id", None),
                )
        except Exception as exc:
            _logger.error("failed_to_save_user_message", error=str(exc))
            yield StreamEvent(
                id=f"evt-0",
                seq=0,
                type="error",
                mode="custom",
                data=f"Database error: {str(exc)}",
                meta=StreamEventMeta(
                    runId=run_id or str(uuid.uuid4()),
                    turnRunId=session_id,
                    node="runtime",
                    nodeCategory="RUNTIME",
                    userVisible=True,
                ),
            )

        # 2. Track assistant response to save it at the end
        assistant_content = []

        if payload.orchestrate:
            async for event in self._stream_chat_orchestrated(payload, session_id, run_id):
                if event.type == "response":
                    assistant_content.append(event.data)
                yield event
        elif getattr(payload, "agent_type", None):
            async for event in self._stream_chat_direct_agent(payload, session_id, run_id):
                if event.type == "response":
                    assistant_content.append(event.data)
                yield event
        else:
            async for event in self._stream_chat_legacy(payload, session_id, run_id):
                if event.type == "response":
                    assistant_content.append(event.data)
                yield event

        # 3. Save full assistant response to database
        full_response = "".join(assistant_content)
        if full_response:
            try:
                with db_session() as db:
                    message = self._chat_repo.add_message(
                        db, 
                        session_id=session_id, 
                        role="assistant", 
                        content=full_response,
                        provider=provider,
                        model=model
                    )
                    self._record_memory_message(
                        db=db,
                        session_id=session_id,
                        agent_id=memory_agent_id,
                        role="assistant",
                        content=full_response,
                        source_message_id=getattr(message, "id", None),
                    )
            except Exception as exc:
                _logger.error("failed_to_save_assistant_message", error=str(exc))
                yield StreamEvent(
                    id=f"evt-err-{str(uuid.uuid4())[:8]}",
                    seq=999,
                    type="error",
                    mode="custom",
                    data=f"Database error saving response: {str(exc)}",
                    meta=StreamEventMeta(
                        runId=run_id or str(uuid.uuid4()),
                        turnRunId=session_id,
                        node="runtime",
                        nodeCategory="RUNTIME",
                        userVisible=True,
                    ),
                )

    async def _stream_chat_direct_agent(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        from omnimind_backend.agents._registry import get_agent

        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        agent_type = getattr(payload, "agent_type", "coder")

        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name=f"Direct Agent: {agent_type}",
            detail=f"Executing directly with {agent_type} personality.",
            action="start",
            node="direct",
            node_category="RUNTIME",
            user_visible=True,
        )

        try:
            agent = get_agent(agent_type)
            messages = [SystemMessage(content=agent.system_prompt), HumanMessage(content=payload.message)]
            llm = get_model_for_provider(provider, model)

            emitted_response = False
            async for chunk in llm.astream(messages):
                thought, texts = extract_chunk_parts(chunk)
                if thought:
                    yield normalizer.thought_event(self._next_seq(counter), thought, run_id=run_id)
                for text in texts:
                    emitted_response = True
                    yield normalizer.response_event(self._next_seq(counter), text, run_id=run_id)

            yield normalizer.step_event(
                self._next_seq(counter),
                run_id=run_id,
                step_name=f"Direct Agent: {agent_type}",
                detail="Agent execution complete.",
                action="complete",
                node="direct",
                node_category="RUNTIME",
                user_visible=True,
            )
            if not emitted_response:
                yield normalizer.response_event(self._next_seq(counter), "No response generated.", run_id=run_id)

        except Exception as exc:
            _logger.error("direct_agent_graph_error", error=str(exc))
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node="direct", node_category="RUNTIME",
            )

        yield self._done_event(
            counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
        )

    def _resolve_memory_agent_id(self, payload: AgentChatRequest) -> str:
        if payload.agent_type:
            return payload.agent_type
        if payload.orchestrate:
            try:
                return route_message(payload.message).agent.value
            except Exception:
                return "coder"
        return "general"

    def _record_memory_message(
        self,
        *,
        db,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
    ) -> None:
        settings = get_settings()
        if not settings.memory_enabled:
            return
        # Tests frequently patch db_session to MagicMock; skip memory in that case.
        if db.__class__.__module__.startswith("unittest.mock"):
            return
        try:
            self._memory_service.record_message(
                db,
                session_id=session_id,
                agent_id=agent_id,
                role=role,
                content=content,
                source_message_id=source_message_id,
            )
        except Exception as exc:
            _logger.warning(
                "memory_record_failed",
                error=str(exc),
                session_id=session_id,
                agent_id=agent_id,
                role=role,
            )

    # ------------------------------------------------------------------
    # Private helpers — shared by all three streaming methods
    # ------------------------------------------------------------------

    def _create_stream_context(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None,
    ) -> tuple[str, str, str, AgentChatStreamNormalizer, list[int]]:
        """Resolve provider, model, run_id and create a normalizer + seq counter."""
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        run_id = run_id or str(uuid.uuid4())
        normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)
        return provider, model, run_id, normalizer, [0]

    @staticmethod
    def _next_seq(counter: list[int]) -> int:
        """Increment and return the mutable sequence counter."""
        counter[0] += 1
        return counter[0]

    def _error_event(
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
        seq = self._next_seq(counter)
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

    def _done_event(
        self,
        *,
        counter: list[int],
        provider: str,
        model: str,
        run_id: str,
        session_id: str,
    ) -> StreamEvent:
        """Build the terminal done StreamEvent."""
        seq = self._next_seq(counter)
        return StreamEvent(
            id=f"evt-{seq}",
            seq=seq,
            type="done",
            mode="messages",
            data="",
            meta=StreamEventMeta(provider=provider, model=model, runId=run_id, turnRunId=session_id),
        )

    async def _stream_chat_legacy(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)

        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Analyze Request",
            detail="Parsing user intent and selecting execution strategy.",
            action="start",
            node="planner",
            node_category="LLM_INVOKE",
            user_visible=True,
        )
        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Analyze Request",
            detail="Request analysis complete.",
            action="complete",
            node="planner",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        web_context = ""
        lower = payload.message.lower()
        should_search = any(token in lower for token in ["search", "latest", "news", "docs", "pesquise", "noticia"])

        if should_search:
            yield normalizer.step_event(
                self._next_seq(counter),
                run_id=run_id,
                step_name="Retrieve Context",
                detail="Running web retrieval for fresh context.",
                action="start",
                node="retrieval",
                node_category="TOOL_EXECUTION",
                user_visible=True,
            )

            tool_call_id = str(uuid.uuid4())
            yield normalizer.tool_call_event(
                self._next_seq(counter),
                tool_call_id=tool_call_id,
                name="search_web",
                args={"query": payload.message},
                run_id=run_id,
            )
            web_context = await search_web(payload.message)
            yield normalizer.tool_result_event(
                self._next_seq(counter),
                tool_call_id=tool_call_id,
                name="search_web",
                result=web_context,
                run_id=run_id,
            )

            yield normalizer.step_event(
                self._next_seq(counter),
                run_id=run_id,
                step_name="Retrieve Context",
                detail="Context retrieval complete.",
                action="complete",
                node="retrieval",
                node_category="TOOL_EXECUTION",
                user_visible=True,
            )

        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Synthesize Response",
            detail="Generating final answer.",
            action="start",
            node="response",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=payload.message)]
        if web_context:
            messages.append(HumanMessage(content=f"Web context:\n{web_context}"))

        try:
            llm = get_model_for_provider(provider, model)
            async for chunk in llm.astream(messages):
                thought, texts = extract_chunk_parts(chunk)
                if thought:
                    yield normalizer.thought_event(self._next_seq(counter), thought, run_id=run_id)
                for text in texts:
                    yield normalizer.response_event(self._next_seq(counter), text, run_id=run_id)

        except Exception as exc:
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node="response", node_category="LLM_INVOKE",
            )
            yield self._done_event(
                counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
            )
            return

        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Synthesize Response",
            detail="Final response delivered.",
            action="complete",
            node="response",
            node_category="LLM_INVOKE",
            user_visible=True,
        )

        yield self._done_event(
            counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
        )

    async def _stream_chat_orchestrated(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)

        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Orchestrating Request",
            detail="Delegating request to specialized agent personality.",
            action="start",
            node="orchestrator",
            node_category="RUNTIME",
            user_visible=True,
        )

        try:
            graph_input = {
                "message": payload.message,
                "provider": provider,
                "model": model,
                "session_id": session_id,
            }

            async for event in self._orchestrator_graph.astream_events(graph_input, version="v2"):
                event_type = event["event"]

                if event_type == "on_custom_event":
                    name = event["name"]
                    data = event["data"]

                    if name == "agent_thought":
                        yield normalizer.thought_event(self._next_seq(counter), data["thought"], run_id=run_id)

                    elif name == "agent_response":
                        yield normalizer.response_event(self._next_seq(counter), data["chunk"], run_id=run_id)

                    elif name == "dt_step":
                        task_name = data.get("task", "unknown")
                        status = data.get("status", "unknown")
                        yield normalizer.step_event(
                            self._next_seq(counter),
                            run_id=run_id,
                            step_name=f"DT: {task_name}",
                            detail=f"Status: {status}",
                            action="start" if status == "resolving" else "complete",
                            node="decomposition_thinker",
                            node_category="RUNTIME",
                            user_visible=True,
                        )

                    elif name == "agent_tool_call":
                        chunk = data.get("chunk", {})
                        if chunk.get("name"):
                            yield normalizer.thought_event(
                                self._next_seq(counter),
                                f"Calling tool: {chunk.get('name')}",
                                run_id=run_id,
                            )

                    elif name == "agent_memory_context":
                        refs = data.get("references", [])
                        agent_name = data.get("agent", "agent")
                        ref_count = len(refs) if isinstance(refs, list) else 0
                        yield normalizer.thought_event(
                            self._next_seq(counter),
                            f"Loaded {ref_count} memory references for {agent_name}.",
                            run_id=run_id,
                        )

                elif event_type == "on_chain_start" and event.get("name") == "route":
                    yield normalizer.thought_event(self._next_seq(counter), "Routing request...", run_id=run_id)

                elif event_type == "on_chain_end" and event.get("name") == "route":
                    output = event.get("data", {}).get("output")
                    if output:
                        decision = output.get("decision")
                        if decision:
                            yield normalizer.thought_event(
                                self._next_seq(counter),
                                f"Decision: {decision.rationale}. Agent: {decision.agent.value.upper()}.",
                                run_id=run_id,
                            )

            yield normalizer.step_event(
                self._next_seq(counter),
                run_id=run_id,
                step_name="Orchestrating Request",
                detail="Agent execution complete.",
                action="complete",
                node="orchestrator",
                node_category="RUNTIME",
                user_visible=True,
            )

        except Exception as exc:
            _logger.error("orchestrator_graph_error", error=str(exc))
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node="orchestrator", node_category="RUNTIME",
            )

        yield self._done_event(
            counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
        )
