import asyncio
import contextlib
import hashlib
import json
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from mindflow_backend.agents.tools.search_web import search_web
from mindflow_backend.graphs.implementations.orchestrator.simple_flow import (
    build_simple_orchestrator_flow,
)
from mindflow_backend.hooks.event_broadcaster import HookEventBroadcaster
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.memory.indexing import is_continuation_prompt
from mindflow_backend.query.hooks import (
    attach_hook_event_bridge as _attach_hook_event_bridge_fn,
)
from mindflow_backend.query.hooks import fire_session_end as _fire_session_end
from mindflow_backend.query.hooks import fire_session_start as _fire_session_start
from mindflow_backend.query.hooks import (
    fire_user_prompt_submit as _fire_user_prompt_submit,
)
from mindflow_backend.query.adapter import adapt_strategy_events as _adapt_strategy_events
from mindflow_backend.query.persistence import (
    dispatch_memory_message as _dispatch_memory_message_fn,
)
from mindflow_backend.query.selector import build_strategy_context as _build_strategy_context
from mindflow_backend.query.selector import select_strategy as _select_strategy
from mindflow_backend.query.persistence import save_message_bg as _save_message_bg_fn
from mindflow_backend.query.persistence import snapshot_json as _snapshot_json_fn
from mindflow_backend.query.persistence import (
    start_execution as _start_execution_fn,
)
from mindflow_backend.query.persistence import (
    sync_session_runtime_state as _sync_session_runtime_state_fn,
)
from mindflow_backend.query.streaming import custom_event as _custom_event_fn
from mindflow_backend.query.streaming import done_event as _done_event_fn
from mindflow_backend.query.streaming import error_event as _error_event_fn
from mindflow_backend.query.streaming import next_seq as _next_seq_fn
from mindflow_backend.runtime.providers import (
    _is_thinking_supported,
    get_model_for_provider,
    resolve_provider_model_for_tools,
)
from mindflow_backend.runtime.streaming.chunk_extract import extract_chunk_parts
from mindflow_backend.runtime.streaming.normalizer import AgentChatStreamNormalizer
from mindflow_backend.runtime.streaming.notifier_policy import should_emit_backend_notifier
from mindflow_backend.schemas.chat.agent import AgentChatRequest, StreamEvent, StreamEventMeta
from mindflow_backend.schemas.orchestration.orchestrator import (
    WorkspaceBinding,
    WorkspacePolicy,
)
from mindflow_backend.services.core import get_worktree_service

try:
    from mindflow_backend.memory import get_memory_service as _get_memory_service
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    _get_memory_service = None
    _logger = get_logger(__name__)
    _logger.warning("memory_service_import_failed", error=str(exc))
else:
    _logger = get_logger(__name__)

try:
    from mindflow_backend.execution_memory import (
        get_execution_memory_service as _get_execution_memory_service,
    )
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    _get_execution_memory_service = None
    _logger.warning("execution_memory_service_import_failed", error=str(exc))

try:
    from mindflow_backend.memory.agent_memory.checkpointer import langgraph_memory
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    langgraph_memory = None
    _logger.warning("langgraph_memory_import_failed", error=str(exc))

try:
    from mindflow_backend.workers.system.publishers.memory_publisher import (
        RabbitMQMemoryTaskPublisher as _RabbitMQMemoryTaskPublisher,
    )
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    _RabbitMQMemoryTaskPublisher = None
    _logger.warning("memory_publisher_import_failed", error=str(exc))

try:
    from mindflow_backend.infra.database.connection import get_db_session as db_session
    from mindflow_backend.storage.postgresql.models import (
        AgentMemoryEvent,
        ChatMessage,
        ChatSession,
    )
except Exception as exc:  # pragma: no cover - import guard for lean test envs
    db_session = None
    AgentMemoryEvent = None
    ChatMessage = None
    ChatSession = None
    _logger.warning("runtime_db_import_failed", error=str(exc))

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

# Maximum number of past user/assistant messages to inject per turn (Mudança 3)
_HISTORY_WINDOW = 8
_ORCHESTRATOR_INTERRUPT_AFTER = ["route", "execute", "respond"]


async def _load_history_messages(session_id: str, limit: int = _HISTORY_WINDOW) -> list[Any]:
    """Load the last ``limit`` user/assistant turns for ``session_id``.

    Returns a list of LangChain HumanMessage / AIMessage objects in chronological
    order, ready to be injected between the system messages and the current user
    message.  Returns an empty list when the DB is unavailable or the session has
    no prior messages.
    """
    if db_session is None or ChatMessage is None:
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

# ── Canonical compiled orchestrator graph singleton ───────────────────────────
# Production orchestration enters here and uses the compiled LangGraph built by
# `graphs/implementations/orchestrator/simple_flow.py`. Compatibility shims may
# re-export this behavior, but they must not construct competing runtimes.
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


class AgentRuntime:
    def __init__(self) -> None:
        # Lazy-load the graph so direct-agent and test paths do not pay the
        # compilation cost unless orchestration is actually requested.
        self._orchestrator_graph = None
        self._memory_service = _get_memory_service() if _get_memory_service else None
        self._execution_memory = _get_execution_memory_service() if _get_execution_memory_service else None
        self._memory_publisher = _RabbitMQMemoryTaskPublisher() if _RabbitMQMemoryTaskPublisher else None
        self._worktree_service = get_worktree_service()
        # Cache only active executions by durable execution_id.
        self._execution_cache: dict[str, Any] = {}

    async def start_session(self, session_id: str, *, cwd: str | None = None) -> None:
        """Executa SessionStart e InstructionsLoaded no runtime canônico."""
        await _fire_session_start(session_id, cwd=cwd)

    async def end_session(
        self,
        session_id: str,
        reason: str = "other",
        *,
        cwd: str | None = None,
    ) -> None:
        """Executa SessionEnd no runtime canônico."""
        await _fire_session_end(session_id, reason, cwd=cwd)

    async def handle_user_prompt(
        self,
        session_id: str,
        prompt: str,
        *,
        cwd: str | None = None,
    ) -> None:
        """Executa UserPromptSubmit no runtime canônico."""
        await _fire_user_prompt_submit(session_id, prompt, cwd=cwd)

    async def _attach_hook_event_bridge(
        self,
        *,
        execution_id: str,
        session_id: str,
    ):
        """Registra bridge de HookEventBroadcaster para execution events."""
        return await _attach_hook_event_bridge_fn(
            execution_id=execution_id,
            session_id=session_id,
            execution_memory=self._execution_memory,
        )

    async def _save_message_bg(
        self,
        session_id: str,
        role: str,
        content: str,
        memory_agent_id: str,
        provider: str | None = None,
        model: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        """Fire-and-forget DB + memory write — runs in background task."""
        await _save_message_bg_fn(
            session_id=session_id,
            role=role,
            content=content,
            memory_agent_id=memory_agent_id,
            memory_service=self._memory_service,
            db_session=db_session,
            chat_message_cls=ChatMessage,
            chat_session_cls=ChatSession,
            memory_publisher=self._memory_publisher,
            provider=provider,
            model=model,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
        )

    def _resolve_execution_mode(self, payload: AgentChatRequest) -> str:
        if payload.orchestrate or self._should_force_structured_analyst_flow(payload):
            return "orchestrated"
        if getattr(payload, "agent_type", None):
            return "direct"
        return "legacy"

    def _requested_workspace_root(self, payload: AgentChatRequest) -> str:
        configured_root = getattr(payload, "folder_path", None)
        if configured_root:
            return configured_root

        settings = get_settings()
        working_path = getattr(settings, "working_path", None)
        if working_path:
            return str(working_path)
        return str(Path.cwd())

    def _needs_workspace_isolation(self, payload: AgentChatRequest) -> bool:
        policy = getattr(payload, "workspace_policy", WorkspacePolicy.AUTO)
        if policy == WorkspacePolicy.WORKTREE:
            return True
        if policy == WorkspacePolicy.SHARED:
            return False

        if getattr(payload, "orchestrate", False) and bool(getattr(payload, "folder_path", None)):
            return True

        agent_type = (getattr(payload, "agent_type", None) or "").strip().lower()
        return agent_type == "coder" and bool(getattr(payload, "folder_path", None))

    async def _prepare_workspace_binding(
        self,
        *,
        payload: AgentChatRequest,
        session_id: str,
        execution_id: str | None = None,
    ) -> WorkspaceBinding | None:
        if self._worktree_service is None:
            return None

        existing_binding = getattr(payload, "workspace_binding", None)
        if isinstance(existing_binding, WorkspaceBinding):
            return existing_binding

        try:
            binding = await self._worktree_service.ensure_workspace(
                session_id=session_id,
                execution_id=execution_id,
                requested_root=self._requested_workspace_root(payload),
                policy=getattr(payload, "workspace_policy", WorkspacePolicy.AUTO),
                needs_isolation=self._needs_workspace_isolation(payload),
            )
        except Exception as exc:
            _logger.warning(
                "workspace_binding_resolution_failed",
                session_id=session_id,
                execution_id=execution_id,
                error=str(exc),
            )
            return None

        payload.workspace_binding = binding
        payload.folder_path = binding.workspace_path
        return binding

    @staticmethod
    def _snapshot_json(value: Any) -> Any:
        return _snapshot_json_fn(value)

    async def _sync_session_runtime_state(
        self,
        *,
        session_id: str | None,
        execution_id: str | None,
    ) -> None:
        await _sync_session_runtime_state_fn(
            execution_memory=self._execution_memory,
            session_id=session_id,
            execution_id=execution_id,
        )

    def _build_context_bundle(self, state_values: dict[str, Any], *, next_nodes: tuple[str, ...] | list[str]) -> dict[str, Any]:
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

    async def _start_execution(
        self,
        *,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None,
        provider: str,
        model: str,
        execution_id: str | None = None,
        status: str = "running",
        stage: str | None = None,
    ) -> Any | None:
        execution_mode = self._resolve_execution_mode(payload)
        workspace_binding = await self._prepare_workspace_binding(
            payload=payload,
            session_id=session_id,
            execution_id=execution_id,
        )
        return await _start_execution_fn(
            execution_memory=self._execution_memory,
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            provider=provider,
            model=model,
            execution_mode=execution_mode,
            workspace_binding=workspace_binding,
            execution_id=execution_id,
            status=status,
            stage=stage,
        )

    async def create_execution(
        self,
        payload: AgentChatRequest,
        *,
        session_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        resolved_session_id = session_id or payload.sessionId or f"sess-{uuid.uuid4()}"
        execution = await self._start_execution(
            payload=payload,
            session_id=resolved_session_id,
            run_id=run_id,
            provider=provider,
            model=model,
            execution_id=getattr(payload, "execution_id", None),
            status="queued",
            stage="routing" if payload.orchestrate or self._should_force_structured_analyst_flow(payload) else "booting",
        )
        if execution is None:
            raise RuntimeError("Execution memory service is unavailable.")

        with contextlib.suppress(Exception):
            await self._execution_memory.append_event(
                execution.id,
                "execution_created",
                {
                    "session_id": resolved_session_id,
                    "root_execution_id": getattr(execution, "root_execution_id", execution.id),
                    "visibility": "internal",
                },
                stage=getattr(execution, "current_stage", None),
            )

        status = await self.get_execution_status(execution.id)
        metadata = dict(status.get("metadata", {}) or {})
        metadata.setdefault("session_id", resolved_session_id)
        status["metadata"] = metadata
        await self._sync_session_runtime_state(
            session_id=resolved_session_id,
            execution_id=status.get("root_execution_id") or execution.id,
        )
        return status

    async def resume_execution(
        self,
        execution_id: str,
        *,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")

        execution = await self._execution_memory.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        if getattr(execution, "mode", None) != "orchestrated":
            raise ValueError("Only orchestrated executions currently support resume.")

        if getattr(execution, "status", "") not in {"paused", "pause_requested", "running", "resuming"}:
            raise ValueError(f"Execution {execution_id} is not resumable from status {getattr(execution, 'status', 'unknown')}.")

        metadata = getattr(execution, "metadata", {}) or {}
        graph_input = metadata.get("graph_input")
        if not isinstance(graph_input, dict) or not graph_input:
            raise ValueError(f"Execution {execution_id} does not have a resumable graph input.")

        payload = AgentChatRequest(
            message=graph_input.get("message") or metadata.get("message") or "",
            provider=graph_input.get("provider") or getattr(execution, "provider", None),
            model=graph_input.get("model") or getattr(execution, "model", None),
            orchestrate=True,
            agent_type=graph_input.get("agent_type"),
            folder_path=graph_input.get("folder_path"),
            workspace_policy=graph_input.get("workspace_policy", WorkspacePolicy.AUTO),
        )
        workspace_payload = metadata.get("workspace")
        if isinstance(workspace_payload, dict):
            with contextlib.suppress(Exception):
                payload.workspace_binding = WorkspaceBinding.model_validate(workspace_payload)
        await self._prepare_workspace_binding(
            payload=payload,
            session_id=graph_input.get("session_id") or execution.session_id,
            execution_id=execution_id,
        )
        await self._execution_memory.mark_status(execution_id, "resuming")
        await self._sync_session_runtime_state(
            session_id=getattr(execution, "session_id", None),
            execution_id=execution_id,
        )

        async for event in self._stream_chat_orchestrated(
            payload,
            graph_input.get("session_id") or execution.session_id,
            run_id,
            execution_id=execution_id,
            resume=True,
            stored_graph_input=graph_input,
        ):
            yield event

    async def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")

        execution = await self._execution_memory.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        snapshot = await self._execution_memory.get_latest_snapshot(execution_id)
        status = getattr(execution, "status", "unknown")
        metadata = dict(getattr(execution, "metadata", {}) or {})
        snapshot_payload = {}
        if snapshot is not None:
            snapshot_payload = (
                getattr(snapshot, "context_json", None)
                or getattr(snapshot, "context_bundle", None)
                or getattr(snapshot, "state_json", None)
                or {}
            )

        progress = getattr(execution, "progress", None)
        if progress is None and snapshot is not None:
            next_nodes = list(getattr(snapshot, "next_nodes", []) or [])
            progress = 1.0 if not next_nodes and status == "completed" else 0.5 if next_nodes else 0.0

        tree = await self._execution_memory.get_execution_tree(execution_id)
        root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
        events = [
            self._snapshot_json(getattr(item, "__dict__", item))
            for item in await self._execution_memory.list_events(root_execution_id, after_id=0)
        ]
        messages = [
            self._snapshot_json(getattr(item, "__dict__", item))
            for item in await self._execution_memory.list_messages(execution_id, include_consumed=True)
        ]
        processes = [
            self._snapshot_json(getattr(item, "__dict__", item))
            for item in await self._execution_memory.list_processes(execution_id)
        ]

        return {
            "execution_id": execution_id,
            "root_execution_id": root_execution_id,
            "parent_execution_id": getattr(execution, "parent_execution_id", None),
            "status": status,
            "stage": getattr(execution, "current_stage", None),
            "paused": status in {"paused", "pause_requested"},
            "can_resume": status in {"paused", "pause_requested"},
            "progress": progress,
            "snapshot": snapshot_payload if isinstance(snapshot_payload, dict) else {"value": snapshot_payload},
            "tree": tree if isinstance(tree, dict) else {"value": tree},
            "events": events,
            "messages": messages,
            "processes": processes,
            "metadata": metadata,
        }

    async def get_execution_events(self, execution_id: str, *, after_id: int = 0) -> list[dict[str, Any]]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")

        execution = await self._execution_memory.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        root_execution_id = getattr(execution, "root_execution_id", None) or execution_id
        rows = await self._execution_memory.list_events(root_execution_id, after_id=after_id)
        return [self._snapshot_json(getattr(row, "__dict__", row)) for row in rows]

    async def send_execution_message(
        self,
        execution_id: str,
        *,
        message_type: str,
        content: str,
        sender_execution_id: str | None = None,
        visibility: str = "internal",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")

        execution = await self._execution_memory.get_execution(execution_id)
        if execution is None:
            raise ValueError(f"Execution not found: {execution_id}")

        message = await self._execution_memory.record_message(
            execution_id=execution_id,
            message_type=message_type,
            sender_execution_id=sender_execution_id,
            recipient_execution_id=execution_id,
            content=content,
            visibility=visibility,
            payload=payload,
            status="pending",
        )
        await self._execution_memory.append_event(
            execution_id,
            "message_received",
            {
                "message_type": message_type,
                "sender_execution_id": sender_execution_id,
                "recipient_execution_id": execution_id,
                "visibility": visibility,
            },
            stage="applying_context" if message_type == "context_update" else getattr(execution, "current_stage", None),
        )
        await self._sync_session_runtime_state(
            session_id=getattr(execution, "session_id", None),
            execution_id=execution_id,
        )

        return {
            "success": True,
            "execution_id": execution_id,
            "root_execution_id": getattr(execution, "root_execution_id", execution_id),
            "parent_execution_id": getattr(execution, "parent_execution_id", None),
            "status": getattr(execution, "status", "unknown"),
            "stage": getattr(execution, "current_stage", None),
            "message": self._snapshot_json(getattr(message, "__dict__", message)),
        }

    async def pause_execution(self, execution_id: str, *, reason: str | None = None) -> dict[str, Any]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")
        await self._execution_memory.request_pause(execution_id=execution_id, reason=reason)
        execution = await self._execution_memory.get_execution(execution_id)
        await self._sync_session_runtime_state(
            session_id=getattr(execution, "session_id", None) if execution is not None else None,
            execution_id=execution_id,
        )
        return await self.get_execution_status(execution_id)

    async def mark_execution_resumed(self, execution_id: str) -> dict[str, Any]:
        if self._execution_memory is None:
            raise RuntimeError("Execution memory service is unavailable.")
        await self._execution_memory.mark_resumed(execution_id=execution_id)
        execution = await self._execution_memory.get_execution(execution_id)
        await self._sync_session_runtime_state(
            session_id=getattr(execution, "session_id", None) if execution is not None else None,
            execution_id=execution_id,
        )
        return await self.get_execution_status(execution_id)

    async def stream_chat(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        settings = get_settings()
        provider = payload.provider or settings.default_provider
        model = payload.model or settings.default_model
        run_id = run_id or str(uuid.uuid4())
        counter = [0]  # Initialize sequence counter for stream events
        memory_agent_id = self._resolve_memory_agent_id(payload)
        execution_mode = self._resolve_execution_mode(payload)
        derived_from_recall = is_continuation_prompt(payload.message)
        await self._prepare_workspace_binding(payload=payload, session_id=session_id)
        execution = None
        requested_execution_id = getattr(payload, "execution_id", None)
        
        if requested_execution_id and requested_execution_id in self._execution_cache:
            execution = self._execution_cache[requested_execution_id]
            _logger.debug("execution_cache_hit", execution_id=requested_execution_id)
        elif self._execution_memory is not None and requested_execution_id:
            execution = await self._execution_memory.get_execution(requested_execution_id)
            if execution is not None:
                with contextlib.suppress(Exception):
                    await self._execution_memory.mark_status(
                        requested_execution_id,
                        "running",
                        stage="routing" if payload.orchestrate or self._should_force_structured_analyst_flow(payload) else "booting",
                    )

        if execution is None:
            execution = await self._start_execution(
                payload=payload,
                session_id=session_id,
                run_id=run_id,
                provider=provider,
                model=model,
                execution_id=requested_execution_id,
            )
            if execution is not None and getattr(execution, "id", None):
                self._execution_cache[getattr(execution, "id")] = execution
        else:
            await self._prepare_workspace_binding(
                payload=payload,
                session_id=session_id,
                execution_id=requested_execution_id,
            )
        execution_id = getattr(execution, "id", None)

        if self._execution_memory is not None and execution_id:
            with contextlib.suppress(Exception):
                await self._execution_memory.mark_status(execution_id, "running", stage="routing")
                await self._execution_memory.append_event(
                    execution_id,
                    "execution_started",
                    {
                        "session_id": session_id,
                        "visibility": "internal",
                    },
                    stage="routing",
                )
            await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)

        hook_event_handler = None
        if execution_id:
            hook_event_handler = await self._attach_hook_event_bridge(
                execution_id=execution_id,
                session_id=session_id,
            )

        await self.handle_user_prompt(
            session_id=session_id,
            prompt=payload.message,
        )

        # 1. Save user message in background — do NOT await before streaming starts
        asyncio.create_task(
            self._save_message_bg(
                session_id=session_id,
                role="user",
                content=payload.message,
                memory_agent_id=memory_agent_id,
                source_status="final",
                derived_from_recall=derived_from_recall,
            )
        )

        # 2. Track assistant response to save it at the end.
        # Use try/finally so the save fires even when the consumer closes the
        # generator early (e.g. agent_controller breaks after "done" event,
        # which triggers .aclose() and would skip code after the last yield).
        assistant_content = []
        assistant_completed = False

        try:
            # ── Unified-engine routing gate ────────────────────────────────
            # When UNIFIED_ENGINE_ENABLED=True the new QueryEngine kernel
            # handles the request. The legacy path is still the default
            # (flag=False) until Phase 5 removes it entirely.
            if settings.unified_engine_enabled:
                from mindflow_backend.query.engine import QueryEngine

                qe: QueryEngine = QueryEngine(
                    providers=[],
                    session_id=session_id,
                )
                strategy = _select_strategy(payload)
                ctx = _build_strategy_context(
                    payload,
                    session_id=session_id,
                    execution_id=execution_id,
                    run_id=run_id,
                    services={"agent": qe},
                )
                provider_str, model_str, current_run_id, normalizer, ev_counter = (
                    self._create_stream_context(payload, session_id, run_id)
                )
                async for stream_event in _adapt_strategy_events(
                    qe.execute(strategy, ctx),
                    provider=provider_str,
                    model=model_str,
                    run_id=current_run_id,
                    session_id=session_id,
                    normalizer=normalizer,
                    counter=ev_counter,
                ):
                    if stream_event.type == "response":
                        assistant_content.append(stream_event.data)
                    elif stream_event.type == "done":
                        assistant_completed = True
                    yield stream_event
                return  # skip legacy path below
            # ── End unified-engine gate ────────────────────────────────────

            # Emit initialization event for visual feedback on cold starts
            is_cold_start = execution_id and getattr(execution, "status", None) == "running"
            if is_cold_start:
                yield self._custom_event(
                    counter=counter,
                    run_id=run_id or str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="initialization",
                    data=json.dumps({
                        "message": "Initializing agent runtime...",
                        "stage": "cold_start"
                    }),
                    agent="system",
                )
            
            if execution_id:
                yield self._custom_event(
                    counter=counter,
                    run_id=run_id or str(uuid.uuid4()),
                    session_id=session_id,
                    event_type="agent_execution_start",
                    data=json.dumps(
                        {
                            "execution_id": execution_id,
                            "root_execution_id": getattr(execution, "root_execution_id", execution_id),
                            "parent_execution_id": getattr(execution, "parent_execution_id", None),
                            "status": getattr(execution, "status", "running"),
                            "stage": getattr(execution, "current_stage", None),
                        }
                    ),
                    agent="orchestrator" if payload.orchestrate or self._should_force_structured_analyst_flow(payload) else getattr(payload, "agent_type", None),
                )

            if payload.orchestrate or self._should_force_structured_analyst_flow(payload):
                async for event in self._stream_chat_orchestrated(payload, session_id, run_id, execution_id=execution_id):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event
            elif getattr(payload, "agent_type", None):
                async for event in self._stream_with_watchdog(
                    source=self._stream_chat_direct_agent(
                        payload,
                        session_id,
                        run_id,
                        execution_id=execution_id,
                    ),
                    payload=payload,
                    session_id=session_id,
                    run_id=run_id,
                    node="direct",
                    node_category="RUNTIME",
                ):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event
            else:
                async for event in self._stream_chat_legacy(payload, session_id, run_id):
                    if event.type == "response":
                        assistant_content.append(event.data)
                    elif event.type == "done":
                        assistant_completed = True
                    yield event

            if self._execution_memory is not None and execution_id:
                execution_record = await self._execution_memory.get_execution(execution_id)
                terminal_statuses = {"completed", "failed", "paused", "pause_requested", "canceled"}
                if execution_record is not None and getattr(execution_record, "status", None) not in terminal_statuses:
                    final_stage = "responding" if execution_mode == "orchestrated" else "finalizing"
                    await self._execution_memory.mark_status(
                        execution_id,
                        "completed",
                        stage=final_stage,
                        progress=1.0,
                    )
                    await self._execution_memory.append_event(
                        execution_id,
                        "execution_completed",
                        {"visibility": "internal"},
                        stage=final_stage,
                    )
                await self._sync_session_runtime_state(session_id=session_id, execution_id=execution_id)
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
                        source_status="final" if assistant_completed else "partial",
                        derived_from_recall=derived_from_recall,
                    )
                )
            if hook_event_handler is not None:
                HookEventBroadcaster.get_instance().unregister(hook_event_handler)
            
            # 4. Ensure 'done' event is always emitted to prevent infinite spinner
            # If streaming failed before emitting 'done', emit it now
            if not assistant_completed:
                yield self._done_event(
                    counter=counter,
                    provider=provider,
                    model=model,
                    run_id=run_id,
                    session_id=session_id,
                )

    async def _stream_chat_direct_agent(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
        *,
        execution_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        _logger.debug(
            "legacy_stream_path_active",
            path="_stream_chat_direct_agent",
            session_id=session_id,
            agent_type=getattr(payload, "agent_type", None),
            deprecation_note="Will be removed after UNIFIED_ENGINE_ENABLED=True is stable in Phase 5",
        )
        from mindflow_backend.agents._registry import get_agent
        from mindflow_backend.agents.tools.base.tool_detection import (
            get_tool_execution_strategy,
        )

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
            tool_strategy = get_tool_execution_strategy(tools)

            resolved_provider, resolved_model = resolve_provider_model_for_tools(
                provider,
                model,
                tools_required=bool(tools),
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
                tools_bound=bool(tools),
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
            if tool_strategy == "callable":
                async for event in self._stream_tool_aware_direct_agent(
                    llm=llm,
                    messages=messages,
                    tools=tools,
                    normalizer=normalizer,
                    counter=counter,
                    run_id=run_id,
                    agent_type=agent_type,
                    session_id=session_id,
                    execution_id=execution_id,
                    sandbox_root=str(sandbox_root) if sandbox_root else None,
                    sandbox_mode=getattr(agent, "sandbox", None),
                ):
                    if event.type == "response":
                        emitted_response = True
                    yield event
            else:
                if tools and tool_strategy != "none":
                    _logger.warning(
                        "direct_agent_non_callable_tools_fallback",
                        agent_type=agent_type,
                        strategy=tool_strategy,
                    )
                async for chunk in llm.astream(messages):
                    thought, texts = extract_chunk_parts(chunk)
                    if thought:
                        _logger.debug("stream_thinking_event", thought_length=len(thought), agent_type=agent_type)
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

    async def _stream_with_watchdog(
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
                exc=exc,
                counter=counter,
                provider=provider,
                model=model,
                run_id=run_id,
                session_id=session_id,
                node=node,
                node_category=node_category,
            )
            yield self._done_event(
                counter=counter,
                provider=provider,
                model=model,
                run_id=run_id,
                session_id=session_id,
            )
        finally:
            if not pending.done():
                pending.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await pending
            if hasattr(iterator, "aclose"):
                with contextlib.suppress(Exception):
                    await iterator.aclose()

    @staticmethod
    def _counts_as_watchdog_progress(event: StreamEvent) -> bool:
        """Only substantive source events reset the watchdog.

        Initial/direct runtime step updates are emitted immediately and should not
        shorten the first-turn budget for slower tool-capable models.
        """
        return event.type != "agent_step"

    @staticmethod
    def _counts_as_tool_watchdog_progress(event: StreamEvent) -> bool:
        """Tool-related progress may need a larger idle budget on slower local models."""
        return event.type in {"tool_call", "tool_result"}

    async def _stream_tool_aware_direct_agent(
        self,
        *,
        llm: Any,
        messages: list[Any],
        tools: list[Any],
        normalizer: AgentChatStreamNormalizer,
        counter: list[int],
        run_id: str,
        agent_type: str,
        session_id: str,
        execution_id: str | None,
        sandbox_root: str | None,
        sandbox_mode: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        from mindflow_backend.agents.tools.base.tool_invocation_callable import (
            invoke_with_callable_tools,
        )
        from mindflow_backend.schemas.tools import ToolContext

        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        async def _dispatch(name: str, payload: dict[str, Any]) -> None:
            await queue.put(("event", (name, payload)))

        async def _runner() -> None:
            try:
                response_text = await invoke_with_callable_tools(
                    llm=llm,
                    messages=messages,
                    callable_tools=tools,
                    tool_context=ToolContext(
                        root_dir=sandbox_root,
                        sandbox_mode=sandbox_mode,
                        session_id=session_id,
                        execution_id=execution_id,
                        metadata={"agent_id": agent_type},
                    ),
                    event_dispatcher=_dispatch,
                    max_iterations=50,
                )
                await queue.put(("response", response_text))
            except Exception as exc:
                await queue.put(("error", exc))
            finally:
                await queue.put(("done", None))

        task = asyncio.create_task(_runner())

        try:
            while True:
                event_type, payload = await queue.get()
                if event_type == "done":
                    break
                if event_type == "error":
                    raise payload
                if event_type == "response":
                    if payload:
                        yield normalizer.response_event(
                            self._next_seq(counter),
                            payload,
                            run_id=run_id,
                            extra_meta={"agent": agent_type},
                        )
                    continue

                name, data = payload
                tool_call_id = data.get("tool_call_id") or str(uuid.uuid4())
                if name == "tool_call_start":
                    yield normalizer.tool_call_event(
                        self._next_seq(counter),
                        tool_call_id=tool_call_id,
                        name=data.get("tool", "tool"),
                        args=data.get("args", {}),
                        run_id=run_id,
                        extra_meta={"agent": agent_type},
                    )
                elif name == "tool_call":
                    yield normalizer.tool_result_event(
                        self._next_seq(counter),
                        tool_call_id=tool_call_id,
                        name=data.get("tool", "tool"),
                        result=data.get("result_preview", ""),
                        run_id=run_id,
                        extra_meta={"agent": agent_type},
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

    async def _dispatch_memory_message(
        self,
        *,
        db,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        settings = get_settings()
        if not settings.memory_enabled:
            return

        queue_enabled = settings.get_feature_flag("rabbitmq_memory_pipeline_enabled", False)
        fallback_enabled = settings.get_feature_flag("rabbitmq_memory_publish_fallback_local", True)

        if queue_enabled and self._memory_publisher is not None:
            try:
                published = await self._memory_publisher.publish_message_recorded(
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                    source_message_id=source_message_id,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
                if published:
                    return
                if not fallback_enabled:
                    return
            except Exception as exc:
                _logger.warning(
                    "memory_publish_failed",
                    error=str(exc),
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                )
                if not fallback_enabled:
                    return

        if self._memory_service is None:
            return

        idempotency_key = f"memory:{source_message_id}" if source_message_id is not None else None

        if db is not None:
            try:
                await self._memory_service.record_message(
                    db,
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                    source_message_id=source_message_id,
                    idempotency_key=idempotency_key,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
                return
            except Exception as exc:
                _logger.warning(
                    "memory_record_with_current_db_failed",
                    error=str(exc),
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                )

        await self._fallback_record_memory_task(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            source_message_id=source_message_id,
            idempotency_key=idempotency_key,
            source_status=source_status,
            derived_from_recall=derived_from_recall,
        )

    async def _fallback_record_memory_task(
        self,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
        idempotency_key: str | None = None,
        source_status: str = "final",
        derived_from_recall: bool = False,
    ) -> None:
        """Memory fallback — opens a fresh db session owned by this task."""
        if self._memory_service is None or db_session is None:
            return
        try:
            async with db_session() as fresh_db:
                await self._memory_service.record_message(
                    fresh_db,
                    session_id=session_id,
                    agent_id=agent_id,
                    role=role,
                    content=content,
                    source_message_id=source_message_id,
                    idempotency_key=idempotency_key,
                    source_status=source_status,
                    derived_from_recall=derived_from_recall,
                )
        except Exception as exc:
            _logger.warning(
                "memory_record_failed",
                error=str(exc),
                session_id=session_id,
                agent_id=agent_id,
                role=role,
            )

    async def _write_agent_memory_event(
        self,
        db,
        *,
        session_id: str,
        agent_id: str,
        role: str,
        content: str,
        source_message_id: int | None,
    ) -> None:
        """Write directly to agent_memory_events using an async session.

        AgentMemoryService is sync-only; this method covers the table in the
        async fallback path without the embedding/window logic.
        """
        if AgentMemoryEvent is None:
            return
        from sqlalchemy import select

        from mindflow_backend.utils.core import estimate_token_count

        token_count = estimate_token_count(content)
        if token_count <= 0:
            return

        # Dedup by source_message_id when available
        if source_message_id is not None:
            existing = (
                await db.execute(
                    select(AgentMemoryEvent)
                    .where(
                        AgentMemoryEvent.session_id == session_id,
                        AgentMemoryEvent.agent_id == agent_id,
                        AgentMemoryEvent.source_message_id == source_message_id,
                    )
                    .limit(1)
                )
            ).scalars().first()
            if existing is not None:
                return

        event = AgentMemoryEvent(
            session_id=session_id,
            agent_id=agent_id,
            role=role,
            content=content,
            token_count=token_count,
            source_message_id=source_message_id,
        )
        db.add(event)
        await db.commit()

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
        return _next_seq_fn(counter)

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
        return _error_event_fn(
            exc=exc,
            counter=counter,
            provider=provider,
            model=model,
            run_id=run_id,
            session_id=session_id,
            node=node,
            node_category=node_category,
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
        return _done_event_fn(
            counter=counter,
            provider=provider,
            model=model,
            run_id=run_id,
            session_id=session_id,
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
        return _custom_event_fn(
            counter=counter,
            run_id=run_id,
            session_id=session_id,
            event_type=event_type,
            data=data,
            agent=agent,
        )

    async def _stream_chat_legacy(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        _logger.debug(
            "legacy_stream_path_active",
            path="_stream_chat_legacy",
            session_id=session_id,
            deprecation_note="Will be removed after UNIFIED_ENGINE_ENABLED=True is stable in Phase 5",
        )
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
            _logger.debug("stream_chat_model_config", provider=provider, model=model, supports_thinking=_is_thinking_supported(model))
            async for chunk in llm.astream(messages):
                _logger.debug("stream_chat_orchestrated_thinking_event", chunk=chunk)
                thought, texts = extract_chunk_parts(chunk)
                if thought:
                    _logger.debug("stream_thinking_event", thought_length=len(thought))
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

    def _decision_payload(self, decision: Any) -> dict[str, Any]:
        """Build a normalized payload preserving full agent identity."""
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
        """Get (agent_type, task) from decision (dict or object)."""
        payload = self._decision_payload(decision)
        return payload["agent_type"], payload["task"]

    def _notifier_payload_for_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_meta: dict[str, Any] | None = None,
    ) -> tuple[str, str, dict[str, Any]]:
        """Build (kind, message, details) for a notifier from tool name, args, and explicit tool metadata."""
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
            "orchestrate": bool(payload.orchestrate),
            "folder_path": getattr(payload, "folder_path", None),
            "workspace_policy": getattr(payload, "workspace_policy", WorkspacePolicy.AUTO).value,
            "workspace": (
                payload.workspace_binding.model_dump(mode="json")
                if isinstance(getattr(payload, "workspace_binding", None), WorkspaceBinding)
                else None
            ),
            "conversation_history": history_dicts,
        }

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
                if self._execution_memory is not None and execution_id:
                    with contextlib.suppress(Exception):
                        await self._execution_memory.mark_status(execution_id, "running", stage="routing")
                        await self._execution_memory.append_event(
                            execution_id,
                            "routing_started",
                            {"visibility": "internal"},
                            stage="routing",
                        )
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
                        if self._execution_memory is not None and execution_id:
                            with contextlib.suppress(Exception):
                                await self._execution_memory.append_event(
                                    execution_id,
                                    "routing_completed",
                                    {
                                        "decision": self._decision_payload(decision),
                                        "visibility": "internal",
                                    },
                                    stage="routing",
                                )
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
                        payload_data = self._decision_payload(decision)
                        current_agent = payload_data["agent_id"]
                        task = payload_data["task"]
                        yield self._custom_event(
                            counter=counter,
                            run_id=run_id,
                            session_id=session_id,
                            event_type="reflection_mode_start",
                            data="",
                        )
                        if self._execution_memory is not None and execution_id:
                            with contextlib.suppress(Exception):
                                await self._execution_memory.mark_status(execution_id, "running", stage="reflecting")
                                await self._execution_memory.append_event(
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
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="agent_delegation_start",
                                data=json.dumps(
                                    {
                                        **payload_data,
                                        "delegated_by": "ORCHESTRATOR",
                                        "task": task,
                                        "step_id": "primary",
                                    }
                                ),
                                agent=current_agent,
                            )
                            if self._execution_memory is not None and execution_id:
                                with contextlib.suppress(Exception):
                                    await self._execution_memory.mark_status(execution_id, "running", stage="delegating")
                                    await self._execution_memory.append_event(
                                        execution_id,
                                        "delegation_created",
                                        {
                                            **payload_data,
                                            "delegated_by": "orchestrator",
                                            "visibility": "internal",
                                        },
                                        stage="delegating",
                                    )
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="specialist_activation",
                                data=json.dumps(
                                    {
                                        **payload_data,
                                        "is_core": payload_data["specialist"] is None,
                                        "step_id": "primary",
                                    }
                                ),
                                agent=current_agent,
                            )
        agent_state["current_agent"] = current_agent

    async def _stream_chat_orchestrated(
        self,
        payload: AgentChatRequest,
        session_id: str,
        run_id: str | None = None,
        *,
        execution_id: str | None = None,
        resume: bool = False,
        stored_graph_input: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        _logger.debug(
            "legacy_stream_path_active",
            path="_stream_chat_orchestrated",
            session_id=session_id,
            orchestrate=getattr(payload, "orchestrate", False),
            deprecation_note="Will be removed after UNIFIED_ENGINE_ENABLED=True is stable in Phase 5",
        )
        provider, model, run_id, normalizer, counter = self._create_stream_context(payload, session_id, run_id)
        agent_state: dict[str, str | None] = {"current_agent": None}

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
            detail="Delegating request to specialized agent personality." if not resume else "Resuming orchestrated execution from the latest checkpoint.",
            action="start",
            node="orchestrator",
            node_category="RUNTIME",
            user_visible=True,
        )

        try:
            history_dicts: list[dict[str, str]] = []
            if stored_graph_input and stored_graph_input.get("conversation_history"):
                history_dicts = list(stored_graph_input.get("conversation_history") or [])
            else:
                _history_msgs = await _load_history_messages(session_id)
                history_dicts = [
                    {
                        "role": "user" if isinstance(m, HumanMessage) else "assistant",
                        "content": m.content,
                    }
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

            if self._execution_memory is not None and execution_id and self._execution_memory is not None:
                execution = await self._execution_memory.get_execution(execution_id)
                if execution is not None:
                    metadata = dict(getattr(execution, "metadata", {}) or {})
                    metadata.setdefault("graph_input", graph_input)
                    await self._execution_memory.mark_status(
                        execution_id,
                        "resuming" if resume else "running",
                        metadata=metadata,
                    )

            if self._execution_memory is None or execution_id is None or langgraph_memory is None:
                if self._orchestrator_graph is None:
                    self._orchestrator_graph = _get_orchestrator_graph()
                async for emitted_event in self._emit_orchestrator_graph_events(
                    graph=self._orchestrator_graph,
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
                        await self._execution_memory.create_snapshot(
                            execution_id=execution_id,
                            checkpoint_id=checkpoint_id,
                            next_nodes=list(next_nodes),
                            state_payload=self._snapshot_json(getattr(state_snapshot, "values", {}) or {}),
                            context_bundle=context_bundle,
                            resumable=bool(next_nodes),
                        )
                        await self._execution_memory.append_event(
                            execution_id,
                            "checkpoint_reached",
                            {
                                "checkpoint_id": checkpoint_id,
                                "next_nodes": list(next_nodes),
                            },
                        )

                        if not next_nodes:
                            await self._execution_memory.mark_status(
                                execution_id,
                                "completed",
                                current_node=None,
                                last_safe_node="completed",
                            )
                            await self._sync_session_runtime_state(
                                session_id=session_id,
                                execution_id=execution_id,
                            )
                            break

                        await self._execution_memory.mark_status(
                            execution_id,
                            "running",
                            current_node=next_nodes[0],
                            last_safe_node=next_nodes[0],
                        )

                        if await self._execution_memory.should_pause(execution_id):
                            await self._execution_memory.append_event(
                                execution_id,
                                "execution_paused",
                                {"next_nodes": list(next_nodes)},
                            )
                            await self._execution_memory.mark_status(
                                execution_id,
                                "paused",
                                current_node=next_nodes[0],
                                last_safe_node=next_nodes[0],
                            )
                            await self._sync_session_runtime_state(
                                session_id=session_id,
                                execution_id=execution_id,
                            )
                            yield self._custom_event(
                                counter=counter,
                                run_id=run_id,
                                session_id=session_id,
                                event_type="notifier",
                                data=json.dumps(
                                    {
                                        "kind": "execution_paused",
                                        "message": "Execução pausada em checkpoint seguro.",
                                        "details": {
                                            "execution_id": execution_id,
                                            "next_node": next_nodes[0],
                                        },
                                    }
                                ),
                            )
                            yield normalizer.step_event(
                                self._next_seq(counter),
                                run_id=run_id,
                                step_name="Orchestrating Request",
                                detail="Execution paused at a safe checkpoint.",
                                action="complete",
                                node="orchestrator",
                                node_category="RUNTIME",
                                user_visible=True,
                            )
                            yield self._done_event(
                                counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
                            )
                            return

                        next_input = None

            yield self._custom_event(
                counter=counter,
                run_id=run_id,
                session_id=session_id,
                event_type="reflection_mode_end",
                data="",
            )
            if self._execution_memory is not None and execution_id:
                with contextlib.suppress(Exception):
                    await self._execution_memory.append_event(
                        execution_id,
                        "reflection_completed",
                        {"visibility": "internal"},
                        stage="responding",
                    )
                    await self._execution_memory.mark_status(execution_id, "running", stage="responding")
                    await self._sync_session_runtime_state(
                        session_id=session_id,
                        execution_id=execution_id,
                    )
            current_agent = agent_state.get("current_agent")
            if current_agent:
                yield self._custom_event(
                    counter=counter,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="agent_delegation_complete",
                    data=json.dumps(
                        {
                            "agent_type": current_agent.split(":", 1)[0].upper(),
                            "agent_id": current_agent,
                            "success": True,
                            "error_message": "",
                            "step_id": "primary",
                        }
                    ),
                    agent=current_agent,
                )
                if self._execution_memory is not None and execution_id:
                    with contextlib.suppress(Exception):
                        await self._execution_memory.append_event(
                            execution_id,
                            "delegation_completed",
                            {"agent_id": current_agent, "success": True, "visibility": "internal"},
                            stage="responding",
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
            if self._execution_memory is not None and execution_id:
                with contextlib.suppress(Exception):
                    await self._execution_memory.append_event(
                        execution_id,
                        "execution_failed",
                        {"error": str(exc)},
                    )
                    await self._execution_memory.mark_status(execution_id, "failed", error=str(exc))
                    await self._sync_session_runtime_state(
                        session_id=session_id,
                        execution_id=execution_id,
                    )
            _logger.error("orchestrator_graph_error", error=str(exc))
            yield self._error_event(
                exc=exc, counter=counter, provider=provider, model=model,
                run_id=run_id, session_id=session_id, node="orchestrator", node_category="RUNTIME",
            )

        yield self._done_event(
            counter=counter, provider=provider, model=model, run_id=run_id, session_id=session_id,
        )
