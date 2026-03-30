"""Runtime Executor - Chat stream execution strategies.

Handles direct agent, orchestrated, legacy, watchdog, and tool-aware
streaming execution modes.
"""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from mindflow_backend.agents.tools.search_web import search_web
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import build_simple_orchestrator_flow
from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.runtime.streaming.notifier_policy import should_emit_backend_notifier
from mindflow_backend.runtime.providers import get_model_for_provider, resolve_provider_model_for_tools
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent, StreamEventMeta

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception as exc:  # pragma: no cover
    _get_memory_service = None
    _logger = get_logger(__name__)
    _logger.warning("memory_service_import_failed", error=str(exc))
else:
    _logger = get_logger(__name__)

try:
    from mindflow_backend.memory.agent_memory.checkpointer import langgraph_memory
except Exception as exc:  # pragma: no cover
    langgraph_memory = None
    _logger.warning("langgraph_memory_import_failed", error=str(exc))

SYSTEM_PROMPT = (
    "You are MindFlow, a pragmatic engineering assistant. "
    "Be concise, factual, and action-oriented. "
    "Always keep outputs clear and useful for software engineering context."
)

_OLLAMA_CODER_TOOL_RUNTIME_PROMPT = (
    "Runtime rules for the current task: use the available tools directly before any prose and do not "
    "describe tool calls in plain text. For new files, call write_file. For existing files, read first "
    "and then edit. Do not output code blocks for files that have not been written yet. "
    "If asked to build a Python CLI task tracker, create exactly app.py, test_app.py, and README.md in "
    "the provided folder. The CLI contract is exact: "
    'python app.py add "text", python app.py list, and python app.py done 1. '
    "Do not invent flags like --task-text or --task-id. Use positional arguments only. "
    "Use simple integer task IDs starting at 1, persist tasks in tasks.json, and keep the implementation "
    "standard-library only. In tests, invoke the CLI with sys.executable instead of the bare python command. "
    "Before the final response, run python -m py_compile app.py test_app.py, then python -m unittest -q, "
    "then a real smoke check with add/list/done, and fix failures if any command fails. "
    "Only send the final response after verification, and include a FINAL_STATUS section with files_created, "
    "tests_passed, and how_to_run."
)

_HISTORY_WINDOW = 8
_ORCHESTRATOR_INTERRUPT_AFTER = ["route", "execute", "respond"]
_ORCHESTRATOR_GRAPH: Any = None


def _get_orchestrator_graph() -> Any:
    global _ORCHESTRATOR_GRAPH
    if _ORCHESTRATOR_GRAPH is None:
        _logger.info("orchestrator_graph_compiling")
        _ORCHESTRATOR_GRAPH = build_simple_orchestrator_flow()
        _logger.info("orchestrator_graph_compiled_and_cached")
    return _ORCHESTRATOR_GRAPH


def _select_direct_agent_system_prompt(
    *,
    agent_type: str,
    base_prompt: str,
    provider: str,
    model: str,
    tools_bound: bool,
) -> str:
    if (
        tools_bound
        and agent_type == "coder"
        and provider == "ollama"
        and model.strip().lower() == "qwen3:8b"
    ):
        return f"{base_prompt}\n\n{_OLLAMA_CODER_TOOL_RUNTIME_PROMPT}"
    return base_prompt


async def _load_history_messages(session_id: str, limit: int = _HISTORY_WINDOW) -> list[Any]:
    """Load the last ``limit`` user/assistant turns for ``session_id``."""
    try:
        from mindflow_backend.infra.database.connection import get_db_session as db_session
        from mindflow_backend.storage.postgresql.models import ChatMessage
    except Exception:
        return []
    try:
        from sqlalchemy import select
        async with db_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .where(ChatMessage.role.in_(["user", "assistant"]))
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            rows = list(reversed(result.scalars().all()))
            lc_msgs: list[Any] = []
            for row in rows:
                if row.role == "user":
                    lc_msgs.append(HumanMessage(content=row.content))
                else:
                    lc_msgs.append(AIMessage(content=row.content))
            return lc_msgs
    except Exception as exc:
        _logger.warning("history_load_failed", session_id=session_id, error=str(exc))
        return []


class RuntimeExecutor:
    """Handles chat stream execution across all execution modes."""

    def __init__(self, runtime: Any = None) -> None:
        """Initialize with a reference to the parent AgentRuntime."""
        self._runtime = runtime
        self._memory_publisher = None
        if runtime is not None:
            self._memory_publisher = getattr(runtime, "_memory_publisher", None)

    def _create_stream_context(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None,
    ) -> tuple[str, str, str, AgentChatStreamNormalizer, list[int]]:
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        run_id = run_id or str(uuid.uuid4())
        normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)
        return provider, model, run_id, normalizer, [0]

    @staticmethod
    def _next_seq(counter: list[int]) -> int:
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

    @staticmethod
    def _snapshot_json(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [RuntimeExecutor._snapshot_json(item) for item in value]
        if isinstance(value, tuple):
            return [RuntimeExecutor._snapshot_json(item) for item in value]
        if isinstance(value, dict):
            return {str(key): RuntimeExecutor._snapshot_json(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return RuntimeExecutor._snapshot_json(value.model_dump(mode="json"))
        if hasattr(value, "value"):
            return RuntimeExecutor._snapshot_json(value.value)
        return str(value)

    def _build_context_bundle(
        self,
        state_values: dict[str, Any],
        *,
        next_nodes: tuple[str, ...] | list[str],
    ) -> dict[str, Any]:
        values = self._snapshot_json(state_values)
        return {
            "objective": values.get("message", ""),
            "decision": values.get("decision"),
            "workflow_plan": values.get("workflow_plan"),
            "memory_context": values.get("memory_context", ""),
            "response": values.get("response", ""),
            "error": values.get("error"),
            "conversation_history": values.get("conversation_history", []),
            "next_nodes": list(next_nodes),
        }

    @staticmethod
    def _counts_as_watchdog_progress(event: StreamEvent) -> bool:
        return event.type != "agent_step"

    @staticmethod
    def _counts_as_tool_watchdog_progress(event: StreamEvent) -> bool:
        return event.type in {"tool_call", "tool_result"}

    def _should_force_structured_analyst_flow(self, payload: AgentChatRequest) -> bool:
        return (
            (getattr(payload, "agent_type", None) or "").lower() == "analyst"
            and bool(getattr(payload, "folder_path", None))
        )

    def _is_direct_response(self, decision: Any) -> bool:
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
        if decision is None:
            return "{}"
        if isinstance(decision, dict):
            return json.dumps(decision)
        if hasattr(decision, "model_dump"):
            return json.dumps(decision.model_dump())
        return json.dumps({"agent": getattr(decision, "agent", None), "task": getattr(decision, "task", "")})

    def _decision_payload(self, decision: Any) -> dict[str, Any]:
        if isinstance(decision, dict):
            agent_role = decision.get("agent_role") or decision.get("agent") or "coder"
            agent_role = getattr(agent_role, "value", agent_role)
            specialist = decision.get("specialist")
            specialist = getattr(specialist, "value", specialist) if specialist is not None else None
            agent_id = decision.get("agent_id") or (
                f"{str(agent_role).lower()}:{specialist}" if specialist else str(agent_role).lower()
            )
            return {
                "agent_type": str(agent_role).upper(),
                "agent_role": str(agent_role).lower(),
                "agent_id": str(agent_id).lower(),
                "specialist": specialist,
                "task": decision.get("task", ""),
            }

        agent_role = getattr(decision, "agent_role", None) or getattr(decision, "agent", None) or "coder"
        agent_role_value = getattr(agent_role, "value", agent_role)
        specialist = getattr(decision, "specialist", None)
        specialist_value = getattr(specialist, "value", specialist) if specialist is not None else None
        agent_id = getattr(decision, "agent_id", None) or (
            f"{str(agent_role_value).lower()}:{specialist_value}" if specialist_value else str(agent_role_value).lower()
        )
        return {
            "agent_type": str(agent_role_value).upper(),
            "agent_role": str(agent_role_value).lower(),
            "agent_id": str(agent_id).lower(),
            "specialist": specialist_value,
            "task": getattr(decision, "task", ""),
        }

    def _decision_agent_task(self, decision: Any) -> tuple[str, str]:
        payload = self._decision_payload(decision)
        return payload["agent_type"], payload["task"]

    def _notifier_payload_for_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_meta: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        meta = tool_meta if isinstance(tool_meta, dict) else {}
        name = str(meta.get("notifier_kind") or tool_name or "").lower()
        family = str(meta.get("family") or "").lower()
        details = {"tool_name": tool_name, **{k: v for k, v in args.items() if v is not None}}
        if meta:
            details["tool_meta"] = meta
            if family:
                details["tool_family"] = family
        if family == "gitnexus" or name.startswith("gitnexus_"):
            if name == "gitnexus_status":
                return ("gitnexus_status", "GitNexus: verificando índice", details)
            if name == "gitnexus_query":
                query = str(args.get("query", "")).strip()
                suffix = f" para {query[:60]}" if query else ""
                return ("gitnexus_query", f"GitNexus: analisando fluxos{suffix}", details)
            if name == "gitnexus_context":
                symbol = args.get("name") or args.get("uid") or args.get("file_path") or "símbolo"
                return ("gitnexus_context", f"GitNexus: carregando contexto de {symbol}", details)
            if name == "gitnexus_impact":
                target = args.get("target") or "símbolo"
                return ("gitnexus_impact", f"GitNexus: calculando impacto de {target}", details)
            return ("tool_start", f"GitNexus: {tool_name}", details)
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

    def _build_orchestrator_graph_input(
        self,
        *,
        payload: AgentChatRequest,
        session_id: str,
        provider: str,
        model: str,
        history_dicts: list[dict[str, str]],
        execution_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "message": payload.message,
            "provider": provider,
            "model": model,
            "session_id": session_id,
            "execution_id": execution_id,
            "agent_type": getattr(payload, "agent_type", None),
            "folder_path": getattr(payload, "folder_path", None),
            "conversation_history": history_dicts,
        }

    # ── Direct Agent Streaming ────────────────────────────────────────

    async def stream_chat_direct_agent(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
        *,
        execution_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        from mindflow_backend.agents._registry import get_agent

        provider, model, run_id, _normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        agent_type = getattr(payload, "agent_type", "coder")

        try:
            agent = get_agent(agent_type)
            base_system_prompt = agent.system_prompt

            sandbox_root = (
                getattr(payload, "folder_path", None)
                or agent.root_dir
                or (getattr(get_settings(), "working_path", None))
            )

            tools: list[Any] = []
            if getattr(agent, "sandbox", None) != "none":
                from mindflow_backend.agents.tools import create_default_registry
                from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
                from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

                sandbox = MindFlowSandbox(
                    root_dir=sandbox_root,
                    read_only=(agent.sandbox == SandboxMode.READ_ONLY),
                )
                registry = create_default_registry(
                    sandbox,
                    session_id=session_id,
                    execution_id=execution_id,
                )
                tools = registry.get_tools_for_agent(agent)

            lc_tools: list[Any] = []
            if tools:
                from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
                lc_tools = to_langchain_tools(tools)

            resolved_provider, resolved_model = resolve_provider_model_for_tools(
                provider,
                model,
                tools_required=bool(lc_tools),
            )
            if (resolved_provider, resolved_model) != (provider, model):
                _logger.warning(
                    "tool_model_fallback_selected",
                    requested_provider=provider,
                    requested_model=model,
                    resolved_provider=resolved_provider,
                    resolved_model=resolved_model,
                )
                provider = resolved_provider
                model = resolved_model

            system_prompt = _select_direct_agent_system_prompt(
                agent_type=agent_type,
                base_prompt=base_system_prompt,
                provider=provider,
                model=model,
                tools_bound=bool(lc_tools),
            )
            messages = [SystemMessage(content=system_prompt)]

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

            for _hist in await _load_history_messages(session_id):
                messages.append(_hist)

            messages.append(HumanMessage(content=payload.message))

            normalizer = AgentChatStreamNormalizer(provider=provider, model=model, turn_run_id=session_id)
            llm = get_model_for_provider(provider, model)

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

            emitted_response = False
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
                    session_id=session_id,
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

    # ── Watchdog Wrapper ──────────────────────────────────────────────

    async def stream_with_watchdog(
        self,
        *,
        source: AsyncGenerator[StreamEvent, None],
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None,
        node: str,
        node_category: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        settings = get_settings()
        timeout_seconds = float(getattr(settings, "agent_stream_timeout_seconds", 0) or 0)
        if timeout_seconds <= 0:
            async for event in source:
                yield event
            return

        initial_timeout_seconds = float(
            getattr(settings, "agent_stream_initial_timeout_seconds", timeout_seconds) or timeout_seconds
        )
        if initial_timeout_seconds <= 0:
            initial_timeout_seconds = timeout_seconds

        tool_progress_timeout_seconds = float(
            getattr(settings, "agent_stream_tool_progress_timeout_seconds", timeout_seconds) or timeout_seconds
        )
        if tool_progress_timeout_seconds <= 0:
            tool_progress_timeout_seconds = timeout_seconds

        heartbeat_seconds = float(
            getattr(settings, "agent_stream_progress_heartbeat_seconds", min(5.0, timeout_seconds))
            or min(5.0, timeout_seconds)
        )
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        iterator = source.__aiter__()
        loop = asyncio.get_running_loop()
        last_progress_at = loop.time()
        meaningful_progress_seen = False
        tool_progress_seen = False
        pending = asyncio.create_task(iterator.__anext__())

        try:
            while True:
                if not meaningful_progress_seen:
                    active_timeout_seconds = initial_timeout_seconds
                elif tool_progress_seen:
                    active_timeout_seconds = tool_progress_timeout_seconds
                else:
                    active_timeout_seconds = timeout_seconds
                elapsed = loop.time() - last_progress_at
                remaining = active_timeout_seconds - elapsed
                if remaining <= 0:
                    yield normalizer.step_event(
                        self._next_seq(counter),
                        run_id=run_id,
                        step_name="Agent Wait",
                        detail="Waiting for agent progress.",
                        action="update",
                        node=node,
                        node_category=node_category,
                        user_visible=True,
                    )
                    raise TimeoutError(
                        f"Agent stream timed out after {active_timeout_seconds:.2f}s without progress"
                    )

                wait_slice = min(heartbeat_seconds, remaining)
                done, _ = await asyncio.wait({pending}, timeout=wait_slice)
                if pending in done:
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        return
                    if self._counts_as_watchdog_progress(event):
                        last_progress_at = loop.time()
                        meaningful_progress_seen = True
                        if self._counts_as_tool_watchdog_progress(event):
                            tool_progress_seen = True
                    counter[0] = max(counter[0], getattr(event, "seq", 0))
                    yield event
                    pending = asyncio.create_task(iterator.__anext__())
                    continue

                yield normalizer.step_event(
                    self._next_seq(counter),
                    run_id=run_id,
                    step_name="Agent Wait",
                    detail="Waiting for agent progress.",
                    action="update",
                    node=node,
                    node_category=node_category,
                    user_visible=True,
                )
        except TimeoutError as exc:
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node=node, node_category=node_category,
            )
            yield self._done_event(
                counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
            )
        finally:
            if not pending.done():
                pending.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pending
            if hasattr(iterator, "aclose"):
                with contextlib.suppress(Exception):
                    await iterator.aclose()

    # ── Tool-Aware Direct Agent ───────────────────────────────────────

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
        session_id: str,
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
                    tool_meta = data.get("tool_meta") or None
                    if tool_name:
                        yield normalizer.tool_call_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            args=tool_args,
                            run_id=run_id,
                            tool_meta=tool_meta,
                            extra_meta=agent_meta,
                        )
                        kind, message, details = self._notifier_payload_for_tool(tool_name, tool_args, tool_meta)
                        if should_emit_backend_notifier(kind):
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="notifier",
                                data=json.dumps({"kind": kind, "message": message, "details": details}),
                                agent=agent_type,
                            )
                elif name == "tool_call":
                    tool_name = data.get("tool", "")
                    tool_args = data.get("args", {}) or {}
                    result_preview = data.get("result_preview", "")
                    tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                    tool_meta = data.get("tool_meta") or None
                    if tool_name and not data.get("tool_call_id"):
                        yield normalizer.tool_call_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            args=tool_args,
                            run_id=run_id,
                            tool_meta=tool_meta,
                            extra_meta=agent_meta,
                        )
                        kind, message, details = self._notifier_payload_for_tool(tool_name, tool_args, tool_meta)
                        if should_emit_backend_notifier(kind):
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="notifier",
                                data=json.dumps({"kind": kind, "message": message, "details": details}),
                                agent=agent_type,
                            )
                    if tool_name and result_preview:
                        yield normalizer.tool_result_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            result=result_preview,
                            run_id=run_id,
                            tool_meta=tool_meta,
                            extra_meta=agent_meta,
                        )
        finally:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    # ── Legacy Streaming ──────────────────────────────────────────────

    async def stream_chat_legacy(
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

        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for _hist in await _load_history_messages(session_id):
            messages.append(_hist)
        messages.append(HumanMessage(content=payload.message))
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

    # ── Orchestrator Graph Events Emitter ─────────────────────────────

    async def _emit_orchestrator_graph_events(
        self,
        *,
        graph: Any,
        graph_input: dict[str, Any] | None,
        config: dict[str, Any] | None,
        normalizer: AgentChatStreamNormalizer,
        counter: list[int],
        run_id: str,
        session_id: str,
        agent_state: dict[str, str | None],
        execution_id: str | None = None,
    ) -> str | None:
        current_agent = agent_state.get("current_agent")
        event_stream: Any
        if config is None:
            event_stream = graph.astream_events(graph_input, version="v2")
        else:
            try:
                event_stream = graph.astream_events(graph_input, config=config, version="v2")
            except TypeError as exc:
                if "config" not in str(exc):
                    raise
                event_stream = graph.astream_events(graph_input, version="v2")

        _execution_memory = getattr(self._runtime, "_execution_memory", None) if self._runtime else None

        async for event in event_stream:
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
                    yield normalizer.response_event(
                        self._next_seq(counter),
                        data["chunk"],
                        run_id=run_id,
                        extra_meta={"agent": current_agent or "orchestrator"},
                    )

                elif name in {"task_step", "dt_step"}:
                    task_name = data.get("task", "unknown")
                    status = data.get("status", "unknown")
                    step_prefix = "DT" if name == "dt_step" else "Task"
                    yield normalizer.step_event(
                        self._next_seq(counter),
                        run_id=run_id,
                        step_name=f"{step_prefix}: {task_name}",
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
                    tool_meta = chunk.get("tool_meta") or None
                    if tool_name:
                        kind, message, details = self._notifier_payload_for_tool(tool_name, args, tool_meta)
                        if should_emit_backend_notifier(kind):
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
                    tool_name = data.get("tool", "")
                    tool_args = data.get("args", {}) or {}
                    tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                    tool_meta = data.get("tool_meta") or None
                    if tool_name:
                        agent_meta = {"agent": current_agent} if current_agent else None
                        yield normalizer.tool_call_event(
                            self._next_seq(counter),
                            tool_call_id=tool_call_id,
                            name=tool_name,
                            args=tool_args,
                            run_id=run_id,
                            tool_meta=tool_meta,
                            extra_meta=agent_meta,
                        )
                        kind, message, details = self._notifier_payload_for_tool(tool_name, tool_args, tool_meta)
                        if should_emit_backend_notifier(kind):
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="notifier",
                                data=json.dumps({"kind": kind, "message": message, "details": details}),
                                agent=current_agent,
                            )

                elif name == "tool_call":
                    tool_name = data.get("tool", "")
                    tool_args = data.get("args", {}) or {}
                    result_preview = data.get("result_preview", "")
                    tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())[:8]
                    tool_meta = data.get("tool_meta") or None
                    agent_meta = {"agent": current_agent} if current_agent else None
                    if tool_name:
                        if not data.get("tool_call_id"):
                            yield normalizer.tool_call_event(
                                self._next_seq(counter),
                                tool_call_id=tool_call_id,
                                name=tool_name,
                                args=tool_args,
                                run_id=run_id,
                                tool_meta=tool_meta,
                                extra_meta=agent_meta,
                            )
                            kind, message, details = self._notifier_payload_for_tool(tool_name, tool_args, tool_meta)
                            if should_emit_backend_notifier(kind):
                                yield self._custom_event(
                                    counter=counter,
                                    run_id=run_id,
                                    session_id=session_id,
                                    event_type="notifier",
                                    data=json.dumps({"kind": kind, "message": message, "details": details}),
                                    agent=current_agent,
                                )
                        if result_preview:
                            yield normalizer.tool_result_event(
                                self._next_seq(counter),
                                tool_call_id=tool_call_id,
                                name=tool_name,
                                result=result_preview,
                                run_id=run_id,
                                tool_meta=tool_meta,
                                extra_meta=agent_meta,
                            )

            elif event_type == "on_chain_start" and event.get("name") == "route":
                if _execution_memory is not None and execution_id:
                    with contextlib.suppress(Exception):
                        await _execution_memory.mark_status(execution_id, "running", stage="routing")
                        await _execution_memory.append_event(
                            execution_id,
                            "routing_started",
                            {"visibility": "internal"},
                            stage="routing",
                        )
                yield self._custom_event(
                    counter=counter, run_id=run_id, session_id=session_id,
                    event_type="orchestrator_thinking", data="Routing request...",
                )
                yield normalizer.thought_event(self._next_seq(counter), "Routing request...", run_id=run_id)

            elif event_type == "on_chain_end" and event.get("name") == "route":
                output = event.get("data", {}).get("output")
                if output:
                    decision = output.get("decision")
                    if decision:
                        if _execution_memory is not None and execution_id:
                            with contextlib.suppress(Exception):
                                await _execution_memory.append_event(
                                    execution_id,
                                    "routing_completed",
                                    {
                                        "decision": self._decision_payload(decision),
                                        "visibility": "internal",
                                    },
                                    stage="routing",
                                )
                        yield self._custom_event(
                            counter=counter, run_id=run_id, session_id=session_id,
                            event_type="orchestrator_thinking_end", data="",
                        )
                        yield self._custom_event(
                            counter=counter, run_id=run_id, session_id=session_id,
                            event_type="orchestrator_decision", data=self._serialize_decision(decision),
                        )
                        payload_data = self._decision_payload(decision)
                        current_agent = payload_data["agent_id"]
                        task = payload_data["task"]
                        yield self._custom_event(
                            counter=counter, run_id=run_id, session_id=session_id,
                            event_type="reflection_mode_start", data="",
                        )
                        if _execution_memory is not None and execution_id:
                            with contextlib.suppress(Exception):
                                await _execution_memory.mark_status(execution_id, "running", stage="reflecting")
                                await _execution_memory.append_event(
                                    execution_id,
                                    "reflection_started",
                                    {"agent_id": current_agent, "visibility": "internal"},
                                    stage="reflecting",
                                )

                        if self._is_direct_response(decision):
                            current_agent = "orchestrator"
                            yield normalizer.thought_event(
                                self._next_seq(counter),
                                "Respondendo diretamente ao usuário.",
                                run_id=run_id,
                            )
                        else:
                            yield self._custom_event(
                                counter=counter, run_id=run_id, session_id=session_id,
                                event_type="agent_delegation_start",
                                data=json.dumps({
                                    **payload_data,
                                    "delegated_by": "ORCHESTRATOR",
                                    "task": task,
                                    "step_id": "primary",
                                }),
                                agent=current_agent,
                            )
                            if _execution_memory is not None and execution_id:
                                with contextlib.suppress(Exception):
                                    await _execution_memory.mark_status(execution_id, "running", stage="delegating")
                                    await _execution_memory.append_event(
                                        execution_id,
                                        "delegation_created",
                                        {**payload_data, "delegated_by": "orchestrator", "visibility": "internal"},
                                        stage="delegating",
                                    )
                            yield self._custom_event(
                                counter=counter, run_id=run_id, session_id=session_id,
                                event_type="specialist_activation",
                                data=json.dumps({
                                    **payload_data,
                                    "is_core": payload_data["specialist"] is None,
                                    "step_id": "primary",
                                }),
                                agent=current_agent,
                            )
        agent_state["current_agent"] = current_agent

    # ── Orchestrated Streaming ────────────────────────────────────────

    async def stream_chat_orchestrated(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
        *,
        execution_id: str | None = None,
        resume: bool = False,
        stored_graph_input: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        agent_state: dict[str, str | None] = {"current_agent": None}

        yield self._custom_event(
            counter=counter, run_id=run_id, session_id=session_id,
            event_type="orchestrator_thinking_start", data="",
        )
        yield normalizer.step_event(
            self._next_seq(counter),
            run_id=run_id,
            step_name="Orchestrating Request",
            detail="Delegating request to specialized agent personality." if not resume else "Resuming orchestrated execution from the latest checkpoint.",
            action="start",
            node="orchestrator",
            node_category="RUNTIME",
            user_visible=True,
        )

        _execution_memory = getattr(self._runtime, "_execution_memory", None) if self._runtime else None

        try:
            history_dicts: list[dict[str, str]] = []
            if stored_graph_input and stored_graph_input.get("conversation_history"):
                history_dicts = list(stored_graph_input.get("conversation_history") or [])
            else:
                _history_msgs = await _load_history_messages(session_id)
                history_dicts = [
                    {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
                    for m in _history_msgs
                ]

            graph_input = stored_graph_input or self._build_orchestrator_graph_input(
                payload=payload,
                session_id=session_id,
                provider=provider,
                model=model,
                history_dicts=history_dicts,
                execution_id=execution_id,
            )

            if _execution_memory is not None and execution_id:
                execution = await _execution_memory.get_execution(execution_id)
                if execution is not None:
                    metadata = dict(getattr(execution, "metadata", {}) or {})
                    metadata.setdefault("graph_input", graph_input)
                    await _execution_memory.mark_status(
                        execution_id,
                        "resuming" if resume else "running",
                        metadata=metadata,
                    )

            if _execution_memory is None or execution_id is None or langgraph_memory is None:
                if getattr(self._runtime, "_orchestrator_graph", None) is None:
                    if self._runtime is not None:
                        self._runtime._orchestrator_graph = _get_orchestrator_graph()
                graph_ref = getattr(self._runtime, "_orchestrator_graph", None) or _get_orchestrator_graph()
                async for emitted_event in self._emit_orchestrator_graph_events(
                    graph=graph_ref,
                    graph_input=graph_input,
                    config=None,
                    normalizer=normalizer,
                    counter=counter,
                    run_id=run_id,
                    session_id=session_id,
                    agent_state=agent_state,
                    execution_id=execution_id,
                ):
                    yield emitted_event
            else:
                async with langgraph_memory() as (checkpointer, store):
                    graph = build_simple_orchestrator_flow(
                        checkpointer=checkpointer,
                        store=store,
                        interrupt_after=_ORCHESTRATOR_INTERRUPT_AFTER,
                    )
                    graph_config = {"configurable": {"thread_id": execution_id}}
                    next_input: dict[str, Any] | None = None if resume else graph_input

                    while True:
                        async for emitted_event in self._emit_orchestrator_graph_events(
                            graph=graph,
                            graph_input=next_input,
                            config=graph_config,
                            normalizer=normalizer,
                            counter=counter,
                            run_id=run_id,
                            session_id=session_id,
                            agent_state=agent_state,
                            execution_id=execution_id,
                        ):
                            yield emitted_event

                        state_snapshot = await graph.aget_state(graph_config)
                        next_nodes = tuple(getattr(state_snapshot, "next", ()) or ())
                        snapshot_config = getattr(state_snapshot, "config", {}) or {}
                        checkpoint_id = (
                            snapshot_config.get("configurable", {}).get("checkpoint_id")
                            if isinstance(snapshot_config, dict)
                            else None
                        )
                        context_bundle = self._build_context_bundle(
                            getattr(state_snapshot, "values", {}) or {},
                            next_nodes=next_nodes,
                        )
                        await _execution_memory.create_snapshot(
                            execution_id=execution_id,
                            checkpoint_id=checkpoint_id,
                            next_nodes=list(next_nodes),
                            state_payload=self._snapshot_json(getattr(state_snapshot, "values", {}) or {}),
                            context_bundle=context_bundle,
                            resumable=bool(next_nodes),
                        )
                        await _execution_memory.append_event(
                            execution_id,
                            "checkpoint_reached",
                            {"checkpoint_id": checkpoint_id, "next_nodes": list(next_nodes)},
                        )

                        if not next_nodes:
                            await _execution_memory.mark_status(execution_id, "completed", current_node=None, last_safe_node="completed")
                            await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)
                            break

                        await _execution_memory.mark_status(execution_id, "running", current_node=next_nodes[0], last_safe_node=next_nodes[0])

                        if await _execution_memory.should_pause(execution_id):
                            await _execution_memory.append_event(execution_id, "execution_paused", {"next_nodes": list(next_nodes)})
                            await _execution_memory.mark_status(execution_id, "paused", current_node=next_nodes[0], last_safe_node=next_nodes[0])
                            await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)
                            yield self._custom_event(
                                counter=counter, run_id=run_id, session_id=session_id,
                                event_type="notifier",
                                data=json.dumps({
                                    "kind": "execution_paused",
                                    "message": "Execução pausada em checkpoint seguro.",
                                    "details": {"execution_id": execution_id, "next_node": next_nodes[0]},
                                }),
                            )
                            yield normalizer.step_event(
                                self._next_seq(counter), run_id=run_id,
                                step_name="Orchestrating Request", detail="Execution paused at a safe checkpoint.",
                                action="complete", node="orchestrator", node_category="RUNTIME", user_visible=True,
                            )
                            yield self._done_event(counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id)
                            return

                        next_input = None

            yield self._custom_event(
                counter=counter, run_id=run_id, session_id=session_id,
                event_type="reflection_mode_end", data="",
            )
            if _execution_memory is not None and execution_id:
                with contextlib.suppress(Exception):
                    await _execution_memory.append_event(execution_id, "reflection_completed", {"visibility": "internal"}, stage="responding")
                    await _execution_memory.mark_status(execution_id, "running", stage="responding")
                    await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)
            current_agent = agent_state.get("current_agent")
            if current_agent:
                yield self._custom_event(
                    counter=counter, run_id=run_id, session_id=session_id,
                    event_type="agent_delegation_complete",
                    data=json.dumps({
                        "agent_type": current_agent.split(":", 1)[0].upper(),
                        "agent_id": current_agent,
                        "success": True,
                        "error_message": "",
                        "step_id": "primary",
                    }),
                    agent=current_agent,
                )
                if _execution_memory is not None and execution_id:
                    with contextlib.suppress(Exception):
                        await _execution_memory.append_event(
                            execution_id, "delegation_completed",
                            {"agent_id": current_agent, "success": True, "visibility": "internal"},
                            stage="responding",
                        )
            yield normalizer.step_event(
                self._next_seq(counter), run_id=run_id,
                step_name="Orchestrating Request", detail="Agent execution complete.",
                action="complete", node="orchestrator", node_category="RUNTIME", user_visible=True,
            )

        except Exception as exc:
            if _execution_memory is not None and execution_id:
                with contextlib.suppress(Exception):
                    await _execution_memory.append_event(execution_id, "execution_failed", {"error": str(exc)})
                    await _execution_memory.mark_status(execution_id, "failed", error=str(exc))
                    await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)
            _logger.error("orchestrator_graph_error", error=str(exc))
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node="orchestrator", node_category="RUNTIME",
            )

        yield self._done_event(
            counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
        )

    # ── Session Sync Helper ───────────────────────────────────────────

    async def _sync_session_runtime_state(
        self,
        *,
        session_id: str | None,
        execution_id: str | None,
    ) -> None:
        _execution_memory = getattr(self._runtime, "_execution_memory", None) if self._runtime else None
        if _execution_memory is None or not session_id or not execution_id:
            return
        try:
            execution = await _execution_memory.get_execution(execution_id)
            if execution is None:
                return

            root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
            root_execution = execution
            if root_execution_id != execution_id:
                loaded_root = await _execution_memory.get_execution(root_execution_id)
                if loaded_root is not None:
                    root_execution = loaded_root

            status = getattr(root_execution, "status", None)
            active = status in {"queued", "running", "pause_requested", "paused", "resuming"}
            state = {
                "agent_runtime": {
                    "latest_execution_id": execution_id,
                    "latest_root_execution_id": root_execution_id,
                    "active_execution_id": root_execution_id if active else None,
                    "root_execution_id": root_execution_id,
                    "status": status,
                    "stage": getattr(root_execution, "current_stage", None),
                    "progress": getattr(root_execution, "progress", None),
                    "can_resume": status in {"paused", "pause_requested"},
                    "active": active,
                    "updated_at": self._snapshot_json(
                        getattr(root_execution, "updated_at", None)
                        or getattr(root_execution, "created_at", None)
                    ),
                }
            }
            await _execution_memory.save_session_runtime_state(
                session_id=session_id,
                execution_id=root_execution_id,
                state=state,
            )
        except Exception as exc:
            _logger.warning(
                "session_runtime_state_sync_failed",
                session_id=session_id,
                execution_id=execution_id,
                error=str(exc),
            )