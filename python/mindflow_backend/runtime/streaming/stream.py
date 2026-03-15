import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from mindflow_backend.agents.tools.search_web import search_web
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import build_simple_orchestrator_flow
from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent, StreamEventMeta

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    _get_memory_service = None
    _logger = get_logger(__name__)
    _logger.warning("memory_service_import_failed", error=str(exc))
else:
    _logger = get_logger(__name__)

try:
    from mindflow_backend.infra.database.connection import get_db_session as db_session
    from mindflow_backend.storage.postgresql.models import ChatMessage, ChatSession
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    db_session = None
    ChatMessage = None
    ChatSession = None
    _logger.warning("runtime_db_import_failed", error=str(exc))

SYSTEM_PROMPT = (
    "You are MindFlow, a pragmatic engineering assistant. "
    "Be concise, factual, and action-oriented. "
    "Always keep outputs clear and useful for software engineering context."
)

# ── Module-level singleton for the compiled LangGraph orchestrator ────────────
# Building the graph compiles the StateGraph (LangGraph compilation) which is
# expensive. We cache it so that it is only compiled ONCE per process, not once
# per HTTP request.
_ORCHESTRATOR_GRAPH: Any = None


def _get_orchestrator_graph() -> Any:
    global _ORCHESTRATOR_GRAPH
    if _ORCHESTRATOR_GRAPH is None:
        _logger.info("orchestrator_graph_compiling")
        _ORCHESTRATOR_GRAPH = build_simple_orchestrator_flow()
        _logger.info("orchestrator_graph_compiled_and_cached")
    return _ORCHESTRATOR_GRAPH


class AgentRuntime:
    def __init__(self) -> None:
        # Lazy-load the graph so direct-agent and test paths do not pay the
        # compilation cost unless orchestration is actually requested.
        self._orchestrator_graph = None
        self._memory_service = _get_memory_service() if _get_memory_service else None

    async def _save_message_bg(
        self,
        session_id: str,
        role: str,
        content: str,
        memory_agent_id: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        """Fire-and-forget DB + memory write — runs in background task."""
        from datetime import UTC, datetime
        if db_session is None or ChatMessage is None or ChatSession is None:
            return
        try:
            async with db_session() as db:
                # Ensure session exists
                sess = await db.get(ChatSession, session_id)
                if not sess:
                    sess = ChatSession(id=session_id, title="New Chat")
                    db.add(sess)

                msg = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    provider=provider if role == "assistant" else None,
                    model=model if role == "assistant" else None,
                )
                db.add(msg)
                sess.updated_at = datetime.now(UTC)
                await db.commit()
                await db.refresh(msg)

                self._record_memory_message(
                    db=db,
                    session_id=session_id,
                    agent_id=memory_agent_id,
                    role=role,
                    content=content,
                    source_message_id=msg.id,
                )
        except Exception as exc:
            _logger.error("bg_save_message_failed", role=role, error=str(exc))

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

        # 1. Save user message in background — do NOT await before streaming starts
        asyncio.create_task(
            self._save_message_bg(
                session_id=session_id,
                role="user",
                content=payload.message,
                memory_agent_id=memory_agent_id,
            )
        )

        # 2. Track assistant response to save it at the end.
        # Use try/finally so the save fires even when the consumer closes the
        # generator early (e.g. agent_controller breaks after "done" event,
        # which triggers .aclose() and would skip code after the last yield).
        assistant_content = []

        try:
            if payload.orchestrate or self._should_force_structured_analyst_flow(payload):
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
        finally:
            # 3. Save full assistant response — runs even if generator is closed early
            full_response = "".join(assistant_content)
            if full_response:
                asyncio.create_task(
                    self._save_message_bg(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        memory_agent_id=memory_agent_id,
                        provider=provider,
                        model=model,
                    )
                )

    async def _stream_chat_direct_agent(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        from mindflow_backend.agents._registry import get_agent

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
            llm = get_model_for_provider(provider, model)
            messages = [SystemMessage(content=agent.system_prompt)]

            sandbox_root = (
                getattr(payload, "folder_path", None)
                or agent.root_dir
                or (getattr(get_settings(), "working_path", None))
            )

            tools = []
            if getattr(agent, "sandbox", None) != "none":
                from mindflow_backend.agents.tools import create_default_registry
                from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
                from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

                sandbox = MindFlowSandbox(
                    root_dir=sandbox_root,
                    read_only=(agent.sandbox == SandboxMode.READ_ONLY),
                )
                registry = create_default_registry(sandbox, session_id=session_id)
                tools = registry.get_tools_for_agent(agent.agent_type)

                if sandbox_root and tools:
                    messages.append(
                        SystemMessage(
                            content=(
                                f"Your working directory (root_dir) is: {sandbox_root}\n"
                                "Use list_directory first, read_file second, and shell only as a fallback "
                                "for navigation or shell tab inspection."
                            )
                        )
                    )

            messages.append(HumanMessage(content=payload.message))

            emitted_response = False
            if tools:
                from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools

                lc_tools = to_langchain_tools(tools)
                if lc_tools:
                    llm_with_tools = llm.bind_tools(lc_tools)
                    async for event in self._stream_tool_aware_direct_agent(
                        llm=llm_with_tools,
                        messages=messages,
                        lc_tools=lc_tools,
                        normalizer=normalizer,
                        counter=counter,
                        run_id=run_id,
                        agent_type=agent_type,
                    ):
                        if event.type == "response":
                            emitted_response = True
                        yield event
                else:
                    async for chunk in llm.astream(messages):
                        thought, texts = extract_chunk_parts(chunk)
                        if thought:
                            yield normalizer.thought_event(self._next_seq(counter), thought, run_id=run_id)
                        for text in texts:
                            emitted_response = True
                            yield normalizer.response_event(self._next_seq(counter), text, run_id=run_id)
            else:
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

    async def _stream_tool_aware_direct_agent(
        self,
        *,
        llm: Any,
        messages: list[Any],
        lc_tools: list[Any],
        normalizer: AgentChatStreamNormalizer,
        counter: list[int],
        run_id: str,
        agent_type: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        from mindflow_backend.agents.tools.base.tool_invocation import stream_with_tools

        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        async def _chunk_dispatch(text: str) -> None:
            await queue.put(("chunk", text))

        async def _event_dispatch(name: str, payload: dict[str, Any]) -> None:
            await queue.put(("event", (name, payload)))

        async def _runner() -> None:
            try:
                await stream_with_tools(
                    llm=llm,
                    messages=messages,
                    lc_tools=lc_tools,
                    chunk_dispatcher=_chunk_dispatch,
                    event_dispatcher=_event_dispatch,
                )
            except Exception as exc:
                await queue.put(("error", exc))
            finally:
                await queue.put(("done", None))

        task = asyncio.create_task(_runner())
        agent_meta = {"agent": agent_type}

        try:
            while True:
                event_kind, payload = await queue.get()
                if event_kind == "done":
                    break
                if event_kind == "error":
                    raise payload
                if event_kind == "chunk":
                    yield normalizer.response_event(
                        self._next_seq(counter),
                        payload,
                        run_id=run_id,
                        extra_meta=agent_meta,
                    )
                    continue

                name, data = payload
                if name == "agent_thought":
                    thought = data.get("thought")
                    if thought:
                        yield normalizer.thought_event(
                            self._next_seq(counter),
                            thought,
                            run_id=run_id,
                            extra_meta=agent_meta,
                        )
                elif name == "tool_call_start":
                    tool_name = data.get("tool", "")
                    tool_args = data.get("args", {}) or {}
                    tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                    if tool_name:
                        yield normalizer.tool_call_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            args=tool_args,
                            run_id=run_id,
                            extra_meta=agent_meta,
                        )
                elif name == "tool_call":
                    tool_name = data.get("tool", "")
                    tool_args = data.get("args", {}) or {}
                    result_preview = data.get("result_preview", "")
                    tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                    if tool_name and not data.get("tool_call_id"):
                        yield normalizer.tool_call_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            args=tool_args,
                            run_id=run_id,
                            extra_meta=agent_meta,
                        )
                    if tool_name and result_preview:
                        yield normalizer.tool_result_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            result=result_preview,
                            run_id=run_id,
                            extra_meta=agent_meta,
                        )
        finally:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _should_force_structured_analyst_flow(self, payload: AgentChatRequest) -> bool:
        return (
            (getattr(payload, "agent_type", None) or "").lower() == "analyst"
            and bool(getattr(payload, "folder_path", None))
        )

    def _resolve_memory_agent_id(self, payload: AgentChatRequest) -> str:
        # Return immediately without LLM call — orchestration routing
        # determines the real agent at execution time, but for memory
        # bucketing we use a lightweight static heuristic.
        if payload.agent_type:
            return payload.agent_type
        if payload.orchestrate:
            return "orchestrator"
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
        if not settings.memory_enabled or self._memory_service is None:
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

    def _custom_event(
        self,
        *,
        counter: list[int],
        run_id: str,
        session_id: str,
        event_type: str,
        data: str = "",
        agent: str | None = None,
    ) -> StreamEvent:
        """Build a custom stream event (orchestrator_*, reflection_*, agent_delegation_*, etc.)."""
        seq = self._next_seq(counter)
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
            type=event_type,  # type: ignore[arg-type]
            mode="custom",
            data=data,
            meta=meta,
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

    def _is_direct_response(self, decision: Any) -> bool:
        """Return True when the orchestrator will answer directly (no specialist delegation)."""
        try:
            from mindflow_backend.schemas.orchestration.orchestrator import ExecutionStrategy
            if isinstance(decision, dict):
                s = decision.get("execution_strategy", "")
                return s == ExecutionStrategy.DIRECT_RESPONSE.value or s == "direct_response"
            s = getattr(decision, "execution_strategy", None)
            return s == ExecutionStrategy.DIRECT_RESPONSE
        except Exception:
            return False

    def _serialize_decision(self, decision: Any) -> str:
        """Serialize decision for orchestrator_decision event."""
        if decision is None:
            return "{}"
        if isinstance(decision, dict):
            return json.dumps(decision)
        if hasattr(decision, "model_dump"):
            return json.dumps(decision.model_dump())
        return json.dumps({"agent": getattr(decision, "agent", None), "task": getattr(decision, "task", "")})

    def _decision_agent_task(self, decision: Any) -> tuple[str, str]:
        """Get (agent_type, task) from decision (dict or object)."""
        if isinstance(decision, dict):
            ag = decision.get("agent")
            agent_type = getattr(ag, "value", ag) if hasattr(ag, "value") else str(ag or "coder")
            task = decision.get("task", "")
            return (agent_type.upper() if isinstance(agent_type, str) else str(agent_type), task)
        agent_type = getattr(decision, "agent", None)
        agent_str = getattr(agent_type, "value", agent_type) if agent_type else "coder"
        task = getattr(decision, "task", "")
        return (str(agent_str).upper(), task)

    def _notifier_payload_for_tool(self, tool_name: str, args: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        """Build (kind, message, details) for a notifier from tool name and args."""
        name = (tool_name or "").lower()
        details = {"tool_name": tool_name, **{k: v for k, v in args.items() if v is not None}}
        if name == "read_file":
            path = args.get("file_path", "")
            offset = args.get("offset")
            limit = args.get("max_lines") or args.get("limit")
            if offset is not None and limit is not None:
                msg = f"Leitura: {path} (linhas {offset + 1}–{offset + limit})"
                details["start_line"] = offset + 1
                details["end_line"] = offset + limit
            else:
                msg = f"Leitura: {path}"
            return ("file_read", msg, details)
        if name in ("write_file", "write"):
            path = args.get("file_path", "")
            return ("file_write", f"Escrita: {path}", details)
        if name in ("edit_file", "edit"):
            path = args.get("file_path", "")
            return ("file_edit", f"Edição: {path}", details)
        if name == "shell_tab_open":
            title = args.get("title") or args.get("tab_id") or "shell"
            return ("shell_tab_open", f"Shell tab: {title}", details)
        if name == "shell_tab_exec":
            command = args.get("command", "")
            return ("shell_tab_exec", f"Shell exec: {command}", details)
        if name == "shell_tab_status":
            tab_id = args.get("tab_id", "")
            return ("shell_tab_status", f"Shell status: {tab_id}", details)
        if name == "shell_tab_close":
            tab_id = args.get("tab_id", "")
            return ("shell_tab_close", f"Shell close: {tab_id}", details)
        if name == "search_web" or "search" in name:
            q = args.get("query", args.get("q", ""))
            return ("search_done", f"Busca: {q[:60]}..." if len(str(q)) > 60 else f"Busca: {q}", details)
        return ("tool_start", f"Tool: {tool_name}", details)

    async def _stream_chat_orchestrated(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        current_agent: str | None = None

        yield self._custom_event(
            counter=counter,
            run_id=run_id,
            session_id=session_id,
            event_type="orchestrator_thinking_start",
            data="",
        )
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
            if self._orchestrator_graph is None:
                self._orchestrator_graph = _get_orchestrator_graph()
            graph_input = {
                "message": payload.message,
                "provider": provider,
                "model": model,
                "session_id": session_id,
                "agent_type": getattr(payload, "agent_type", None),
                "folder_path": getattr(payload, "folder_path", None),
            }

            async for event in self._orchestrator_graph.astream_events(graph_input, version="v2"):
                event_type = event["event"]

                if event_type == "on_custom_event":
                    name = event["name"]
                    data = event["data"]

                    if name == "agent_thought":
                        thought_meta = {"agent": current_agent} if current_agent else None
                        yield normalizer.thought_event(
                            self._next_seq(counter),
                            data["thought"],
                            run_id=run_id,
                            extra_meta=thought_meta,
                        )

                    elif name == "agent_response":
                        # Attribute to the actual specialist agent that produced this response.
                        yield normalizer.response_event(
                            self._next_seq(counter),
                            data["chunk"],
                            run_id=run_id,
                            extra_meta={"agent": current_agent or "orchestrator"},
                        )

                    elif name == "task_step":
                        task_name = data.get("task", "unknown")
                        status = data.get("status", "unknown")
                        yield normalizer.step_event(
                            self._next_seq(counter),
                            run_id=run_id,
                            step_name=f"Task: {task_name}",
                            detail=f"Status: {status}",
                            action="start" if status == "resolving" else "complete",
                            node="task_thinker",
                            node_category="RUNTIME",
                            user_visible=True,
                        )

                    elif name == "agent_tool_call":
                        chunk = data.get("chunk", {})
                        tool_name = chunk.get("name") or "tool"
                        args = chunk.get("args") or {}
                        if tool_name:
                            yield normalizer.thought_event(
                                self._next_seq(counter),
                                f"Calling tool: {tool_name}",
                                run_id=run_id,
                                extra_meta={"agent": current_agent} if current_agent else None,
                            )
                            # Flexible notifier for UI (file ops, tools, etc.)
                            kind, message, details = self._notifier_payload_for_tool(tool_name, args)
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="notifier",
                                data=json.dumps({"kind": kind, "message": message, "details": details}),
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
                        yield self._custom_event(
                            counter=counter,
                            run_id=run_id,
                            session_id=session_id,
                            event_type="notifier",
                            data=json.dumps({
                                "kind": "context_loaded",
                                "message": f"Contexto carregado: {ref_count} referências para {agent_name}",
                                "details": {"count": ref_count, "source": agent_name},
                            }),
                        )

                    elif name == "tool_call_start":
                        # Emitted BEFORE tool execution — shows tool as 'calling' immediately
                        tool_name = data.get("tool", "")
                        tool_args = data.get("args", {}) or {}
                        tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                        if tool_name:
                            agent_meta = {"agent": current_agent} if current_agent else None
                            yield normalizer.tool_call_event(
                                self._next_seq(counter),
                                tool_call_id=tool_call_id,
                                name=tool_name,
                                args=tool_args,
                                run_id=run_id,
                                extra_meta=agent_meta,
                            )

                    elif name == "tool_call":
                        tool_name = data.get("tool", "")
                        tool_args = data.get("args", {}) or {}
                        result_preview = data.get("result_preview", "")
                        tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                        agent_meta = {"agent": current_agent} if current_agent else None
                        if tool_name:
                            # Only emit tool_call_event if no prior tool_call_start was sent
                            if not data.get("tool_call_id"):
                                yield normalizer.tool_call_event(
                                    self._next_seq(counter),
                                    tool_call_id=tool_call_id,
                                    name=tool_name,
                                    args=tool_args,
                                    run_id=run_id,
                                    extra_meta=agent_meta,
                                )
                            if result_preview:
                                yield normalizer.tool_result_event(
                                    self._next_seq(counter),
                                    tool_call_id=tool_call_id,
                                    name=tool_name,
                                    result=result_preview,
                                    run_id=run_id,
                                    extra_meta=agent_meta,
                                )

                elif event_type == "on_chain_start" and event.get("name") == "route":
                    yield self._custom_event(
                        counter=counter,
                        run_id=run_id,
                        session_id=session_id,
                        event_type="orchestrator_thinking",
                        data="Routing request...",
                    )
                    yield normalizer.thought_event(self._next_seq(counter), "Routing request...", run_id=run_id)

                elif event_type == "on_chain_end" and event.get("name") == "route":
                    output = event.get("data", {}).get("output")
                    if output:
                        decision = output.get("decision")
                        if decision:
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="orchestrator_thinking_end",
                                data="",
                            )
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="orchestrator_decision",
                                data=self._serialize_decision(decision),
                            )
                            agent_type, task = self._decision_agent_task(decision)
                            current_agent = agent_type.lower()
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="reflection_mode_start",
                                data="",
                            )

                            if self._is_direct_response(decision):
                                # Orchestrator answers directly — no delegation card on frontend.
                                # Emit a lightweight event so the UI can show "responding directly".
                                current_agent = "orchestrator"
                                yield normalizer.thought_event(
                                    self._next_seq(counter),
                                    "Respondendo diretamente ao usuário.",
                                    run_id=run_id,
                                )
                            else:
                                # Real specialist delegation — show the delegation card.
                                yield self._custom_event(
                                    counter=counter,
                                    run_id=run_id,
                                    session_id=session_id,
                                    event_type="agent_delegation_start",
                                    data=json.dumps({
                                        "agent_type": agent_type,
                                        "delegated_by": "ORCHESTRATOR",
                                        "task": task,
                                    }),
                                )
                                yield self._custom_event(
                                    counter=counter,
                                    run_id=run_id,
                                    session_id=session_id,
                                    event_type="specialist_activation",
                                    data=json.dumps({"agent_type": agent_type, "is_core": True}),
                                )
                                rationale = (
                                    getattr(decision, "rationale", "")
                                    or (decision.get("rationale") if isinstance(decision, dict) else "")
                                )
                                yield normalizer.thought_event(
                                    self._next_seq(counter),
                                    f"Delegando para **{agent_type}**. {rationale}",
                                    run_id=run_id,
                                )

            yield self._custom_event(
                counter=counter,
                run_id=run_id,
                session_id=session_id,
                event_type="reflection_mode_end",
                data="",
            )
            if current_agent:
                yield self._custom_event(
                    counter=counter,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="agent_delegation_complete",
                    data=json.dumps({"agent_type": current_agent.upper(), "success": True, "error_message": ""}),
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
