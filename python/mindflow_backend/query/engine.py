"""QueryEngine — unified execution engine for MindFlow.

This is the single execution engine for MindFlow, combining:
- Context building from multiple providers (original QueryEngine)
- Token budget enforcement (original QueryEngine)
- File caching via SessionFileCache (original QueryEngine)
- Auto-compact service (original QueryEngine)
- Agent task delegation (original DelegationEngine)
- Workspace isolation via WorkTreeService (original DelegationEngine)
- CommunicationBus for P2P (original DelegationEngine)
- MissionLauncher integration (original DelegationEngine)
- Fallback management (original DelegationEngine)
- Memory-grounded optimization (original DelegationEngine)
- A2A external calls (original DelegationEngine)

Usage:
    engine = QueryEngine(
        providers=[GitProvider(), FileProvider(), MemoryProvider()],
        budget=TokenBudget(max_tokens=200_000),
        permission_manager=permission_manager,
    )
    # Context building
    context = await engine.build_context(query="How does auth work?")
    # Agent delegation
    result = await engine.delegate_task(task, session)
    # Workflow step execution
    result = await engine.execute_workflow_step(step, ...)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.communication.bus.communication_bus import (
    CommunicationBus,
    get_communication_bus,
)
from mindflow_backend.communication.mixins.agent_communication import AgentCommunicationMixin
from mindflow_backend.execution_memory import get_execution_memory_service
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.infra.resilience.orchestration_fallback import (
    FallbackContext,
    get_orchestration_fallback_manager,
)
from mindflow_backend.permissions.types import PermissionContext, PermissionMode
from mindflow_backend.query.budget.auto_compact import AutoCompactService
from mindflow_backend.query.budget.token_counter import TokenBudget
from mindflow_backend.query.cache.file_cache import SessionFileCache, create_session_cache
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import (
    Priority,
    SandboxMode,
    WorkspaceBinding,
    WorkspacePolicy,
)
from mindflow_backend.schemas.orchestration.workflow import WorkflowStep
from mindflow_backend.services.core import get_worktree_service

if TYPE_CHECKING:
    from mindflow_backend.permissions.manager import PermissionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Context Provider Protocol
# ---------------------------------------------------------------------------


class ContextProvider(Protocol):
    """Protocol for context data providers.

    Each provider fetches contextual data from a different source:
    - GitProvider: git status, diffs, branch info
    - FileProvider: file contents, directory listings
    - MemoryProvider: session/project memory retrieval
    - MCPProvider: MCP server resources and tools

    Providers return (source_label, content, priority) tuples.
    """

    @property
    def name(self) -> str:
        """Provider name for logging."""
        ...

    async def fetch(self, query: str, budget: TokenBudget) -> str | None:
        """Fetch context data.

        Args:
            query: The user's query (for relevant context)
            budget: Token budget to respect (check remaining before fetching)

        Returns:
            Context text or None if nothing to contribute
        """
        ...

    @property
    def priority(self) -> int:
        """Priority for ordering and trimming (higher = more important)."""
        return 50


# ---------------------------------------------------------------------------
# Query Context
# ---------------------------------------------------------------------------


@dataclass
class QueryContext:
    """Assembled context for a query execution."""

    query: str
    system_prompt: str
    assembled_context: str
    budget: TokenBudget
    permission_context: PermissionContext
    metadata: dict[str, int] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.budget.total_tokens


# ---------------------------------------------------------------------------
# Query Engine
# ---------------------------------------------------------------------------


class QueryEngine:
    """Unified execution engine for MindFlow.

    This is the single entry point for all execution in MindFlow:
    - Context building from providers (Git, File, Memory, MCP)
    - Token budget enforcement
    - Agent task delegation
    - Workspace isolation
    - P2P communication
    - Mission execution
    - Fallback management

    Combines the original QueryEngine and DelegationEngine into one unified engine.
    """

    def __init__(
        self,
        providers: list[ContextProvider],
        budget: TokenBudget | None = None,
        system_prompt: str = "",
        permission_manager: PermissionManager | None = None,
        session_id: str | None = None,
        use_file_cache: bool = True,
        execution_memory: Any | None = None,
    ) -> None:
        # Original QueryEngine components
        self._providers = sorted(providers, key=lambda p: -p.priority)
        self._budget = budget or TokenBudget()
        self._system_prompt = system_prompt
        self._permission_manager = permission_manager

        # File cache for avoiding re-reads
        self._file_cache: SessionFileCache | None = None
        if use_file_cache and session_id:
            self._file_cache = create_session_cache(session_id)
            logger.info(
                "query_engine_file_cache_enabled",
                session_id=session_id,
            )

        # Auto-compact service for context management
        self._auto_compact = AutoCompactService(
            file_cache=self._file_cache,
            session_id=session_id,
        )

        # DelegationEngine components
        self.settings = get_settings()
        self._execution_memory = execution_memory or get_execution_memory_service()
        self._worktree_service = get_worktree_service()
        self._fallback_manager = get_orchestration_fallback_manager()
        self._register_fallback_handlers()

        # Communication bus (optional, graceful degradation)
        self._comm_bus: CommunicationBus | None = None
        try:
            self._comm_bus = get_communication_bus()
        except Exception:
            pass  # Bus not available — continue without P2P

        # MissionLauncher (Phase 2B) — lazy init, None until needed
        self._mission_launcher: Any | None = None

    @property
    def budget(self) -> TokenBudget:
        return self._budget

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def file_cache(self) -> SessionFileCache | None:
        """Get the file cache instance."""
        return self._file_cache

    @property
    def auto_compact(self) -> AutoCompactService:
        """Get the auto-compact service instance."""
        return self._auto_compact

    async def read_file_with_cache(
        self,
        file_path: str,
        encoding: str = "utf-8",
    ) -> str | None:
        """Read a file using the session cache.

        Uses SessionFileCache to avoid re-reading unchanged files.

        Args:
            file_path: Path to the file.
            encoding: File encoding (default: utf-8).

        Returns:
            File content as string, or None if file doesn't exist.
        """
        if self._file_cache:
            return await self._file_cache.get_or_read(file_path, encoding)

        # Fallback: read directly without cache
        try:
            with open(file_path, encoding=encoding) as f:
                return f.read()
        except (FileNotFoundError, PermissionError):
            return None

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats: dict[str, Any] = {
            "file_cache_enabled": self._file_cache is not None,
            "auto_compact_enabled": True,
        }

        if self._file_cache:
            stats["file_cache"] = self._file_cache.get_stats()

        return stats

    async def build_context(
        self,
        query: str,
        permission_context: PermissionContext | None = None,
    ) -> QueryContext:
        """Build query context from all providers within budget.

        Executes providers in priority order (highest first).
        Each provider receives the current budget state so it can
        limit its output accordingly.

        Args:
            query: The user's query
            permission_context: Current permission state

        Returns:
            QueryContext with assembled context and budget state
        """
        self._budget.reset()

        # Add system prompt first (highest priority)
        if self._system_prompt:
            self._budget.add_context(
                source="system_prompt",
                content=self._system_prompt,
                priority=100,
            )

        # Fetch from each provider within budget
        metadata: dict[str, int] = {}
        for provider in self._providers:
            if self._budget.is_near_limit():
                logger.warning(
                    f"Skipping provider '{provider.name}' — near budget limit "
                    f"({self._budget.utilization:.0%})"
                )
                break

            try:
                content = await provider.fetch(query, self._budget)
                if content:
                    tokens = self._budget.add_context(
                        source=f"provider:{provider.name}",
                        content=content,
                        priority=provider.priority,
                    )
                    metadata[f"tokens_{provider.name}"] = tokens
                    logger.debug(
                        f"Provider '{provider.name}' contributed {tokens} tokens"
                    )
            except Exception:
                logger.exception(f"Provider '{provider.name}' failed")

        # Trim if over budget
        if self._budget.is_over_budget():
            trimmed = self._budget.trim_to_fit()
            for ctx in trimmed:
                logger.warning(
                    f"Trimmed context section from '{ctx.source}' "
                    f"({ctx.token_count} tokens, priority={ctx.priority})"
                )

        assembled = self._budget.assemble()

        return QueryContext(
            query=query,
            system_prompt=self._system_prompt,
            assembled_context=assembled,
            budget=self._budget,
            permission_context=permission_context or PermissionContext(
                mode=PermissionMode.DEFAULT,
            ),
            metadata=metadata,
        )

    async def fetch_provider_summary(
        self, provider_name: str, query: str
    ) -> str | None:
        """Fetch context from a single provider (for debugging/inspection)."""
        for provider in self._providers:
            if provider.name == provider_name:
                return await provider.fetch(query, self._budget)
        raise ValueError(f"Provider '{provider_name}' not found")

    def add_provider(self, provider: ContextProvider) -> None:
        """Add a context provider at runtime."""
        self._providers.append(provider)
        self._providers.sort(key=lambda p: -p.priority)
        logger.info(f"Added provider: '{provider.name}' (priority={provider.priority})")

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a context provider by name."""
        before = len(self._providers)
        self._providers = [
            p for p in self._providers if p.name != provider_name
        ]
        removed = len(self._providers) < before
        if removed:
            logger.info(f"Removed provider: '{provider_name}'")
        return removed

    def get_budget_summary(self) -> dict[str, Any]:
        """Get current budget utilization summary."""
        summary = self._budget.summary()
        summary["by_provider"] = self._budget.get_usage_by_source()
        return summary

    def reset(self) -> None:
        """Reset engine state for a new conversation."""
        self._budget.reset()
        logger.info("QueryEngine reset")

    # ---------------------------------------------------------------------------
    # Strategy Dispatcher (unified-engine kernel entrypoint)
    # ---------------------------------------------------------------------------

    async def execute(
        self,
        strategy: Any,  # QueryStrategy — late-bound to avoid circular imports
        context: Any,  # StrategyContext — late-bound to avoid circular imports
    ):
        """Dispatch a request to the chosen execution strategy.

        This is the canonical entrypoint of the unified kernel. Gated by the
        ``UNIFIED_ENGINE_ENABLED`` feature flag — legacy paths do NOT route
        through here until Phase 3 of the migration plan.

        Args:
            strategy: A ``QueryStrategy`` enum value or its string form.
            context: A ``StrategyContext`` dataclass with message, services,
                tools and metadata needed by the strategy.

        Yields:
            Stream events as dicts. The strategy terminates by yielding a
            ``{"type": "final", ...}`` or a ``{"type": "system", "is_error":
            True}`` event.
        """
        # Late imports to keep the query module lightweight at import time
        # and avoid circular dependencies with strategies.*
        from mindflow_backend.query.strategies import (
            QueryStrategy,
            StrategyContext,
            get_strategy,
        )

        # Use structlog for structured kwargs (module-level ``logger`` here is
        # stdlib-only — a pre-existing inconsistency in this file).
        struct_logger = get_logger(__name__)

        # Normalize strategy into the enum value
        if isinstance(strategy, str):
            strategy_enum = QueryStrategy(strategy)
        elif isinstance(strategy, QueryStrategy):
            strategy_enum = strategy
        else:
            raise TypeError(
                f"execute() expected QueryStrategy or str, got {type(strategy).__name__}"
            )

        if not isinstance(context, StrategyContext):
            raise TypeError(
                f"execute() expected StrategyContext, got {type(context).__name__}"
            )

        # Token budget defaults to the engine's budget if not supplied by caller.
        # Use replace() so we don't mutate the caller's dataclass in-place.
        if context.token_budget is None:
            from dataclasses import replace

            context = replace(context, token_budget=self._budget)

        strategy_impl = get_strategy(strategy_enum)

        struct_logger.info(
            "queryengine_execute_start",
            strategy=strategy_enum.value,
            session_id=context.session_id,
            execution_id=context.execution_id,
            provider=context.provider,
            model=context.model,
        )

        try:
            async for event in strategy_impl.run(context):
                yield event
        except Exception as exc:  # noqa: BLE001 - surfaced to caller
            struct_logger.error(
                "queryengine_execute_failed",
                strategy=strategy_enum.value,
                session_id=context.session_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            yield {
                "type": "system",
                "content": f"QueryEngine.execute({strategy_enum.value}) failed: {exc}",
                "is_error": True,
            }
        finally:
            struct_logger.info(
                "queryengine_execute_end",
                strategy=strategy_enum.value,
                session_id=context.session_id,
            )

    # ---------------------------------------------------------------------------
    # Execution Memory Helpers (from ExecutionMemoryMixin)
    # ---------------------------------------------------------------------------

    async def _start_child_execution(
        self,
        *,
        task: Any,
        session_id: str | None,
        root_execution_id: str | None,
        parent_execution_id: str | None,
    ) -> Any | None:
        """Start a child execution record for the delegated task."""
        if self._execution_memory is None or not session_id or not root_execution_id:
            return None
        try:
            return await self._execution_memory.start_execution(
                session_id=session_id,
                agent_id=task.agent_id or task.agent.value,
                goal=task.objective,
                root_execution_id=root_execution_id,
                parent_execution_id=parent_execution_id or root_execution_id,
                execution_role="delegated_agent",
                owner_execution_id=root_execution_id,
                status="running",
                stage="booting",
                metadata={
                    "task_id": str(task.task_id),
                    "objective": task.objective,
                    "scope": list(task.scope or []),
                    "expected_output": task.expected_output,
                    "context_from_session": task.context_from_session,
                    "workspace": (
                        task.workspace_binding.model_dump(mode="json")
                        if getattr(task, "workspace_binding", None) is not None
                        else None
                    ),
                },
            )
        except Exception as exc:
            logger.warning("delegation_child_execution_start_failed", error=str(exc))
            return None

    async def _append_execution_event(
        self,
        execution_id: str | None,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        stage: str | None = None,
        message: str | None = None,
    ) -> None:
        """Append an event to the execution timeline."""
        if self._execution_memory is None or not execution_id:
            return
        try:
            await self._execution_memory.append_event(
                execution_id,
                event_type,
                payload or {},
                stage=stage,
                message=message,
            )
        except Exception as exc:
            logger.warning(
                "delegation_event_persist_failed",
                execution_id=execution_id,
                error=str(exc),
            )

    async def _mark_execution_status(
        self,
        execution_id: str | None,
        status: str,
        **updates: Any,
    ) -> None:
        """Update the execution status."""
        if self._execution_memory is None or not execution_id:
            return
        try:
            await self._execution_memory.mark_status(execution_id, status, **updates)
        except Exception as exc:
            logger.warning(
                "delegation_status_persist_failed",
                execution_id=execution_id,
                error=str(exc),
            )

    async def _record_result_message(
        self,
        *,
        child_execution_id: str,
        recipient_execution_id: str | None,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Record a result message from child to parent execution."""
        if self._execution_memory is None:
            return
        try:
            await self._execution_memory.record_message(
                execution_id=child_execution_id,
                message_type=message_type,
                sender_execution_id=child_execution_id,
                recipient_execution_id=recipient_execution_id,
                content=content,
                visibility="internal",
                payload=payload,
                status="pending",
            )
        except Exception as exc:
            logger.warning(
                "delegation_message_persist_failed",
                execution_id=child_execution_id,
                error=str(exc),
            )

    def _make_event_dispatcher(self, execution_id: str | None):
        """Create an event dispatcher function for tool invocations."""

        async def _dispatch(event_name: str, payload: dict[str, Any]) -> None:
            if execution_id:
                await self._append_execution_event(
                    execution_id,
                    event_name,
                    payload,
                    stage="working",
                )
            try:
                from langchain_core.callbacks.manager import adispatch_custom_event

                await adispatch_custom_event(event_name, payload)
            except Exception:
                pass

        return _dispatch

    def _make_before_iteration(self, execution_id: str | None):
        """Create a before-iteration hook for consuming pending messages."""

        async def _before_iteration(messages: list[Any], _iteration: int) -> None:
            if self._execution_memory is None or not execution_id:
                return

            try:
                pending = await self._execution_memory.consume_pending_messages(
                    execution_id=execution_id
                )
            except Exception as exc:
                logger.warning(
                    "delegation_pending_message_load_failed",
                    execution_id=execution_id,
                    error=str(exc),
                )
                return

            for message in pending:
                content = getattr(message, "content", "")
                if not content:
                    continue
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Additional context update received while you were working.\n"
                            f"{content}"
                        ),
                    }
                )
                await self._append_execution_event(
                    execution_id,
                    "message_consumed",
                    {
                        "message_id": getattr(message, "id", None),
                        "message_type": getattr(message, "message_type", None),
                    },
                    stage="applying_context",
                )

            if pending:
                await self._mark_execution_status(
                    execution_id, "running", stage="working"
                )

        return _before_iteration

    # ---------------------------------------------------------------------------
    # Fallback Management
    # ---------------------------------------------------------------------------

    def _register_fallback_handlers(self) -> None:
        """Register fallback handlers for delegation engine."""

        async def delegation_fallback(ctx: FallbackContext) -> DelegationResult:
            """Fallback handler for delegation - return error result."""
            logger.warning(
                "delegation_engine_fallback_triggered",
                original_error=str(ctx.original_error),
            )
            task = ctx.metadata.get("task")
            return DelegationResult(
                task_id=task.task_id if task else "unknown",
                agent=task.agent if task else None,
                agent_role=task.agent_role if task else None,
                specialist=task.specialist if task else None,
                agent_id=task.agent_id if task else None,
                status="failed",
                key_findings="",
                full_output=f"Delegation failed: {str(ctx.original_error)}",
                confidence=0.0,
                error_message=str(ctx.original_error),
            )

        self._fallback_manager.register_fallback_handler(
            "delegation_engine", delegation_fallback
        )

    # ---------------------------------------------------------------------------
    # Mission Launcher
    # ---------------------------------------------------------------------------

    def _get_mission_launcher(self) -> Any | None:
        """Lazy init MissionLauncher with graceful degradation.

        Returns MissionLauncher if available, None otherwise.
        Never raises — if anything goes wrong, returns None to fallback.
        """
        if self._mission_launcher is not None:
            return self._mission_launcher

        try:
            from mindflow_backend.execution.missions.mission_launcher import (
                get_mission_launcher as _get_launcher,
            )
            self._mission_launcher = _get_launcher(comm_bus=self._comm_bus)
            logger.debug("mission_launcher_initialized")
        except Exception:
            logger.warning("mission_launcher_unavailable")
            self._mission_launcher = None  # Ensure not retried

        return self._mission_launcher

    # ---------------------------------------------------------------------------
    # Delegation Methods (from DelegationEngine)
    # ---------------------------------------------------------------------------

    async def delegate_task(
        self,
        task: DelegationTask,
        session: Any,  # OrchestratorSession
        *,
        session_id: str | None = None,
        root_execution_id: str | None = None,
        parent_execution_id: str | None = None,
    ) -> DelegationResult:
        """Execute a delegated task and return structured results."""

        logger.info(
            "delegation_started",
            agent=task.agent.value,
            task_id=str(task.task_id),
            objective=task.objective,
        )

        # Fase C: Intercept calls mapped to an external A2A address
        if task.agent_id and task.agent_id.startswith("a2a://"):
            from mindflow_backend.communication.a2a.a2a_client import A2AClient
            logger.info("delegating_to_a2a_external_agent", target=task.agent_id)
            target_url = task.agent_id.replace("a2a://", "http://")
            return await A2AClient.call_external_agent(task, target_url)

        # Phase 2B: Check if task has mission_type and launcher is available
        mission_type = getattr(task, "metadata", {}).get("mission_type") if getattr(task, "metadata", None) else None
        launcher = self._get_mission_launcher()

        if mission_type and launcher:
            try:
                from mindflow_backend.schemas.orchestration.communication import (
                    MissionGraphType,
                )
                mgt = MissionGraphType(mission_type)
                agent_id = task.agent_id or (
                    f"{task.agent.value}:{task.specialist.value}"
                    if task.specialist
                    else task.agent.value
                )

                mission_result = await launcher.launch_mission(
                    agent_id=agent_id,
                    mission_type=mgt,
                    task=task.objective,
                    session_id=session_id or session.id if session else "unknown",
                    comm_bus=self._comm_bus,
                    max_iterations=getattr(task, "max_iterations", 500),
                )

                # Convert MissionResult to DelegationResult
                result_data = mission_result.to_delegation_result_data()
                return DelegationResult(
                    task_id=task.task_id,
                    agent=task.agent,
                    agent_role=task.agent_role or task.agent,
                    specialist=task.specialist,
                    agent_id=agent_id,
                    status=result_data["status"],
                    key_findings=result_data.get("key_findings", ""),
                    full_output=result_data.get("full_output", ""),
                    confidence=result_data.get("confidence", 0.0),
                    tokens_consumed=result_data.get("tokens_consumed", 0),
                    error_message=result_data.get("error_message"),
                )
            except Exception as exc:
                logger.warning(
                    "mission_launcher_failed_falling_back",
                    extra={"error": str(exc)},
                )
                # Fallback to regular delegation

        task = await self._resolve_task_workspace(
            task,
            session_id=session_id,
            execution_id=None,
        )

        child_execution = await self._start_child_execution(
            task=task,
            session_id=session_id,
            root_execution_id=root_execution_id,
            parent_execution_id=parent_execution_id,
        )
        child_execution_id = getattr(child_execution, "id", None)
        task = await self._resolve_task_workspace(
            task,
            session_id=session_id,
            execution_id=child_execution_id,
        )
        await self._append_execution_event(
            child_execution_id,
            "delegation_started",
            {
                "task_id": str(task.task_id),
                "objective": task.objective,
                "scope": list(task.scope or []),
            },
            stage="booting",
        )

        # Execute with fallback (includes retry logic automatically)
        fallback_result = await self._fallback_manager.execute_with_fallback(
            component="delegation_engine",
            primary_func=lambda: self._delegation_primary(task, session, session_id, child_execution_id, parent_execution_id, root_execution_id),
            context={"task": task},
        )

        if fallback_result.success:
            result = fallback_result.result
        else:
            # Ultimate fallback if everything fails
            logger.error(
                "delegation_ultimate_fallback",
                error=fallback_result.error,
            )
            result = DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                agent_role=task.agent_role or task.agent,
                specialist=task.specialist,
                agent_id=task.agent_id,
                status="failed",
                key_findings="",
                full_output=f"Delegation failed: {fallback_result.error}",
                confidence=0.0,
                error_message=fallback_result.error,
            )

        # Handle failure case for execution tracking
        if result.status == "failed" and child_execution_id:
            await self._append_execution_event(
                child_execution_id,
                "delegation_failed",
                {
                    "task_id": str(task.task_id),
                    "error": result.error_message,
                    "success": False,
                },
                stage="finalizing",
            )
            await self._mark_execution_status(
                child_execution_id,
                "failed",
                stage="finalizing",
                error=result.error_message,
            )

        return result

    async def _delegation_primary(
        self,
        task: DelegationTask,
        session: Any,
        session_id: str | None,
        child_execution_id: str | None,
        parent_execution_id: str | None,
        root_execution_id: str | None,
    ) -> DelegationResult:
        """Primary delegation logic."""
        # Get the target agent
        agent = get_agent(
            task.agent_role or task.agent,
            specialist=task.specialist,
            agent_id=task.agent_id,
            session_id=session_id,
        )

        # Inject P2P communication capability if bus is available
        if self._comm_bus and self._comm_bus.is_available:
            agent_id_str = task.agent_id or (
                f"{task.agent.value}:{task.specialist.value}"
                if task.specialist
                else task.agent.value
            )
            agent.comm = AgentCommunicationMixin(
                agent_id=agent_id_str,
                bus=self._comm_bus,
            )
            logger.debug(
                "delegation_comm_injected",
                extra={"agent_id": agent_id_str, "task_id": str(task.task_id)},
            )

        # Prepare messages for the agent
        messages = [
            {"role": "system", "content": agent.system_prompt}
        ]

        # Add context if provided
        if task.context_from_session:
            messages.append(
                {"role": "system", "content": f"Relevant context from previous delegations:\n{task.context_from_session}"}
            )

        # Add memory context if provided (RAG from agent history)
        if getattr(task, "memory_context", None) and task.memory_context.strip():
            messages.append(
                {
                    "role": "system",
                    "content": f"Memory Context (RAG from agent history):\n{task.memory_context}"
                }
            )
            # Add memory-grounded instruction if enabled
            if getattr(task, "memory_grounded", False):
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "MEMORY-GROUNDED TURN: responda primeiro usando o Memory Context. "
                            "Só use ferramentas se a memória for insuficiente ou ambígua."
                        ),
                    }
                )

        # Add conversation history if provided
        if getattr(task, "conversation_history", None):
            for item in task.conversation_history:
                messages.append({"role": item["role"], "content": item["content"]})

        # Add the main task
        task_prompt = self._format_task_for_agent(task)
        messages.append({"role": "user", "content": task_prompt})

        # Set up sandbox and tools
        sandbox = self._create_sandbox_for_agent(agent, task)
        tool_registry = create_default_registry(
            sandbox,
            session_id=session_id,
            execution_id=child_execution_id,
        )

        # Get authorized tools (none for sandbox NONE agents)
        if agent.sandbox == SandboxMode.NONE:
            tools = []
        else:
            tools = tool_registry.get_tools_for_agent(agent)

        if child_execution_id and (parent_execution_id or root_execution_id):
            from mindflow_backend.agents.tools.orchestration.notify_orchestrator import (
                NotifyOrchestratorTool,
            )

            notify_tool = NotifyOrchestratorTool(execution_memory=self._execution_memory)
            notify_tool.execution_id = child_execution_id
            notify_tool.parent_execution_id = parent_execution_id or root_execution_id
            if session_id:
                notify_tool.session_id = session_id
            tools.append(notify_tool)

        # Inject root_dir into system prompt when tools are available
        if sandbox.cwd and tools:
            messages.insert(
                1,
                {
                    "role": "system",
                    "content": (
                        f"Your working directory (root_dir) is: {sandbox.cwd}\n"
                        "Use this path as the base for all filesystem operations "
                        "unless the user specifies an absolute path."
                    ),
                },
            )

        # Get LLM instance
        llm = get_model_for_provider(
            self.settings.default_provider,
            getattr(task, "model", None) or self.settings.default_model
        )

        if child_execution_id:
            await self._mark_execution_status(
                child_execution_id,
                "running",
                stage="working",
                progress=0.1,
            )

        # Bind tools and run with tool invocation loop if tools are available
        response_text = ""

        # Memory-grounded optimization: try direct response first if memory context is available
        is_memory_grounded = getattr(task, "memory_grounded", False)
        has_memory_context = getattr(task, "memory_context", None) and task.memory_context.strip()

        if is_memory_grounded and has_memory_context and tools:
            # Try direct response without tools first
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)

            # Check if response indicates need for tool follow-up
            if not self._needs_tool_follow_up(response_text):
                # Response is sufficient, return without tools
                key_findings = response_text[:500] + "... [truncated]" if len(response_text) > 1000 else response_text
                return DelegationResult(
                    task_id=task.task_id,
                    agent=task.agent,
                    agent_role=task.agent_role or task.agent,
                    specialist=task.specialist,
                    agent_id=task.agent_id,
                    status="completed",
                    key_findings=key_findings,
                    full_output=response_text,
                    files_analyzed=[],
                    symbols_found=[],
                    confidence=0.9,  # High confidence for memory-grounded responses
                    tokens_consumed=len(response_text.split()) + len(messages) * 10,
                )
            # If needs_tool_follow_up, continue to tool execution below

        if tools:
            from mindflow_backend.agents.tools.base.tool_detection import (
                get_tool_execution_strategy,
                separate_tools,
            )
            from mindflow_backend.schemas.tools.context import ToolContext

            strategy = get_tool_execution_strategy(tools)

            if strategy == "callable":
                # Phase 3: All tools are CallableTools → use direct execution
                from mindflow_backend.agents.tools.base.tool_invocation_callable import (
                    invoke_with_callable_tools,
                )

                callable_tools, _ = separate_tools(tools)

                # Build ToolContext for callable execution
                # Get permission context from agent's sandbox configuration
                permission_context = self._build_permission_context(agent, task)
                
                tool_context = ToolContext(
                    permission_context=permission_context,
                    metadata={
                        "session_id": session_id,
                        "execution_id": child_execution_id,
                        "agent_id": task.agent_id,
                    },
                    root_dir=sandbox.cwd,
                    sandbox_mode=agent.sandbox,
                    session_id=session_id,
                    execution_id=child_execution_id,
                )

                response_text = await invoke_with_callable_tools(
                    llm=llm,
                    messages=messages,
                    callable_tools=callable_tools,
                    tool_context=tool_context,
                    event_dispatcher=self._make_event_dispatcher(child_execution_id),
                    before_iteration=self._make_before_iteration(child_execution_id),
                    max_iterations=max(1, getattr(task, "max_iterations", 1) * 5),
                )

            else:
                # No tools or unsupported tool type - skip tool execution
                logger.warning(
                    "no_tools_or_unsupported_type",
                    strategy=strategy,
                    tool_count=len(tools),
                )

        if not response_text:
            # Fallback: no tools or tool conversion failed
            response = await llm.ainvoke(messages)
            content = getattr(response, "content", None)
            if isinstance(content, str):
                response_text = content
            elif isinstance(content, list):
                parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        parts.append(part)
                    elif isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                response_text = "".join(parts)
            else:
                response_text = str(content) if content else ""

        # Estimate token consumption (rough approximation)
        tokens_consumed = len(response_text.split()) + len(messages) * 10  # Rough estimate

        # Create structured result
        result = DelegationResult(
            task_id=task.task_id,
            agent=task.agent,
            agent_role=task.agent_role or task.agent,
            specialist=task.specialist,
            agent_id=task.agent_id,
            status="completed",
            key_findings=self._extract_key_findings(response_text, task.expected_output),
            full_output=response_text,
            files_analyzed=self._extract_files_mentioned(response_text),
            symbols_found=self._extract_symbols_mentioned(response_text),
            confidence=0.8,  # Agent's self-assessed confidence
            tokens_consumed=tokens_consumed,
        )

        logger.info(
            "delegation_completed",
            agent=task.agent.value,
            task_id=str(task.task_id),
            tokens=tokens_consumed,
            confidence=result.confidence,
        )

        if child_execution_id:
            await self._record_result_message(
                child_execution_id=child_execution_id,
                recipient_execution_id=parent_execution_id or root_execution_id,
                message_type="final_result",
                content=result.full_output or result.key_findings,
                payload={
                    "task_id": str(task.task_id),
                    "confidence": result.confidence,
                    "files_analyzed": list(result.files_analyzed or []),
                },
            )
            await self._append_execution_event(
                child_execution_id,
                "delegation_completed",
                {
                    "task_id": str(task.task_id),
                    "confidence": result.confidence,
                    "success": True,
                },
                stage="finalizing",
            )
            await self._mark_execution_status(
                child_execution_id,
                "completed",
                stage="finalizing",
                progress=1.0,
            )

        return result

    def _needs_workspace_isolation(self, task: DelegationTask) -> bool:
        if task.workspace_policy == WorkspacePolicy.WORKTREE:
            return True
        if task.workspace_policy == WorkspacePolicy.SHARED:
            return False
        return bool(task.root_dir)

    async def _resolve_task_workspace(
        self,
        task: DelegationTask,
        *,
        session_id: str | None,
        execution_id: str | None,
    ) -> DelegationTask:
        if (
            self._worktree_service is None
            or not session_id
            or not task.root_dir
        ):
            return task

        if (
            isinstance(task.workspace_binding, WorkspaceBinding)
            and (
                execution_id is None
                or task.workspace_binding.execution_id == execution_id
            )
        ):
            return task.model_copy(update={"root_dir": task.workspace_binding.workspace_path})

        try:
            binding = await self._worktree_service.ensure_workspace(
                session_id=session_id,
                execution_id=execution_id,
                requested_root=task.root_dir,
                policy=task.workspace_policy,
                needs_isolation=self._needs_workspace_isolation(task),
            )
        except Exception as exc:
            logger.warning(
                "delegation_workspace_resolution_failed",
                session_id=session_id,
                execution_id=execution_id,
                error=str(exc),
            )
            return task

        return task.model_copy(
            update={
                "root_dir": binding.workspace_path,
                "workspace_binding": binding,
            }
        )

    def _format_task_for_agent(self, task: DelegationTask) -> str:
        """Format the delegation task for the specific agent."""

        task_prompt = f"""You are a {task.agent.value} agent.

OBJECTIVE: {task.objective}

SCOPE: {', '.join(task.scope) if task.scope else 'Determine appropriate scope based on objective'}

EXCLUSIONS: {', '.join(task.exclusions) if task.exclusions else 'None'}

EXPECTED OUTPUT FORMAT: {task.expected_output or "Provide a complete solution following your agent's best practices"}

PRIORITY: {task.priority.value}

MAX ITERATIONS: {task.max_iterations}

"""

        if task.context_from_session:
            task_prompt += f"""
PREVIOUS CONTEXT:
{task.context_from_session}

Use this context to inform your work, but focus on the current objective.
"""

        return task_prompt

    def _build_permission_context(self, agent, task: DelegationTask) -> dict[str, Any]:
        """Build permission context based on agent sandbox configuration and task.
        
        Args:
            agent: The agent configuration
            task: The delegation task
            
        Returns:
            Dictionary with permission settings
        """
        # Base permissions from agent sandbox mode
        sandbox_mode = getattr(agent, 'sandbox', None)
        
        permissions = {
            "sandbox_mode": str(sandbox_mode) if sandbox_mode else "none",
            "filesystem": {
                "read": True,  # Always allow read
                "write": sandbox_mode != SandboxMode.READ_ONLY if sandbox_mode else False,
                "delete": sandbox_mode == SandboxMode.READ_WRITE if sandbox_mode else False,
            },
            "network": {
                "http_requests": True,
                "external_apis": True,
            },
            "execution": {
                "shell_commands": sandbox_mode != SandboxMode.READ_ONLY if sandbox_mode else False,
                "code_execution": True,
            },
            "task_scope": {
                "allowed_paths": [task.root_dir] if task.root_dir else [],
                "exclusions": task.exclusions or [],
            },
        }
        
        return permissions

    def _create_sandbox_for_agent(self, agent, task=None):
        """Create appropriate sandbox for the agent."""
        # Priority: task.root_dir > settings.working_path > None
        sandbox_root = (
            (task.root_dir if task and getattr(task, "root_dir", None) else None)
            or (self.settings.working_path if hasattr(self.settings, "working_path") else None)
        )

        return MindFlowSandbox(
            root_dir=sandbox_root,
            read_only=(agent.sandbox == SandboxMode.READ_ONLY),
        )

    def _extract_key_findings(self, response: str, expected_output: str) -> str:
        """Extract key findings from agent response based on expected output format.
        
        Uses expected_output hint to guide extraction strategy.
        """
        if not response:
            return ""
        
        # Parse expected_output to determine extraction strategy
        expected_lower = (expected_output or "").lower()
        
        # Strategy 1: Summary/Overview - extract first paragraph or executive summary
        if any(keyword in expected_lower for keyword in ["summary", "overview", "executive"]):
            # Look for summary section or take first substantial paragraph
            lines = response.split('\n')
            summary_lines = []
            in_summary = False
            
            for line in lines:
                line_stripped = line.strip().lower()
                # Detect summary section headers
                if any(marker in line_stripped for marker in ['summary:', 'overview:', 'executive summary:', 'key findings:']):
                    in_summary = True
                    continue
                # Stop at next major section
                if in_summary and line_stripped.endswith(':') and len(line_stripped) > 3:
                    break
                if in_summary and line.strip():
                    summary_lines.append(line.strip())
                    if len(summary_lines) >= 5:  # Limit to 5 lines
                        break
            
            if summary_lines:
                return ' '.join(summary_lines)
            
            # Fallback: first paragraph if no summary section found
            first_para = response.split('\n\n')[0] if '\n\n' in response else response[:500]
            return first_para[:800] if len(first_para) > 800 else first_para
        
        # Strategy 2: List/Bullet points - extract list items
        if any(keyword in expected_lower for keyword in ["list", "bullet", "items", "points"]):
            import re
            # Find bullet points or numbered items
            bullet_pattern = r'^[\s]*[-•*\d]+[.\s]+(.+)$'
            matches = re.findall(bullet_pattern, response, re.MULTILINE)
            if matches:
                return '\n'.join(f"- {m[:200]}" for m in matches[:10])  # Top 10 items, max 200 chars each
        
        # Strategy 3: Code/Technical - extract code blocks and explanations
        if any(keyword in expected_lower for keyword in ["code", "implementation", "technical", "solution"]):
            import re
            # Find code blocks
            code_blocks = re.findall(r'```[\w]*\n(.*?)```', response, re.DOTALL)
            if code_blocks:
                # Return first code block with some context
                first_block = code_blocks[0][:500]
                return f"Code solution provided:\n```\n{first_block}\n```"
            
            # Look for function/class definitions
            func_pattern = r'(def\s+\w+\s*\([^)]*\):|class\s+\w+[^(]*:)'  
            func_matches = re.findall(func_pattern, response)
            if func_matches:
                return f"Implemented {len(func_matches)} function(s)/class(es): {', '.join(func_matches[:3])}"
        
        # Strategy 4: Analysis/Review - extract conclusions and recommendations
        if any(keyword in expected_lower for keyword in ["analysis", "review", "assessment", "evaluation"]):
            import re
            # Look for conclusion/recommendation sections
            conclusion_patterns = [
                r'(?:conclusion|concluding|in conclusion|summary)[s]?:?\s*(.+?)(?=\n\n|\Z)',
                r'(?:recommendation|suggestion)[s]?:?\s*(.+?)(?=\n\n|\Z)',
            ]
            for pattern in conclusion_patterns:
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    conclusion = match.group(1).strip()[:800]
                    return conclusion
        
        # Default strategy: Compress long responses intelligently
        if len(response) > 1000:
            # Try to find a good breaking point (end of sentence/paragraph)
            truncated = response[:800]
            # Find last sentence end
            last_period = truncated.rfind('.')
            last_newline = truncated.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > 400:  # Only use if we have substantial content
                return response[:break_point] + "... [truncated]"
            return response[:500] + "... [truncated for context efficiency]"
        
        return response

    def _extract_files_mentioned(self, response: str) -> list[str]:
        """Extract file paths mentioned in response."""
        # Simple regex to find file-like patterns
        file_pattern = r'\b[\w\-_\/\.]+\.(?:py|js|ts|json|yaml|yml|md|txt|sql)\b'
        matches = re.findall(file_pattern, response, re.IGNORECASE)
        return list(set(matches))

    def _extract_symbols_mentioned(self, response: str) -> list[str]:
        """Extract function/class/symbol names mentioned in response."""
        # Simple regex to find code symbols
        symbol_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\('
        matches = re.findall(symbol_pattern, response)
        return list(set(matches))

    def _needs_tool_follow_up(self, response_text: str) -> bool:
        """Check if response indicates need for tool usage (memory-grounded logic).

        Used when memory_grounded is True to determine if the agent needs
        to use tools despite having memory context available.

        Args:
            response_text: The agent's response text

        Returns:
            True if response indicates insufficient context and needs tools
        """
        normalized = (response_text or "").strip().lower()
        if not normalized:
            return True
        insufficiency_markers = (
            "não tenho contexto suficiente",
            "preciso investigar",
            "não encontrei",
            "não sei",
            "insufficient context",
            "need to inspect",
            "contexto insuficiente",
            "need more information",
            "cannot determine",
        )
        return any(marker in normalized for marker in insufficiency_markers)

    # ---------------------------------------------------------------------------
    # Workflow Step Execution (from StepRunner)
    # ---------------------------------------------------------------------------

    async def execute_workflow_step(
        self,
        *,
        step: WorkflowStep,
        user_message: str,
        provider: str,
        model: str,
        session_id: str,
        folder_path: str | None = None,
        memory_context: str = "",
        memory_grounded: bool = False,
        conversation_history: list[dict[str, str]] | None = None,
        prior_context: str = "",
        chunk_dispatcher: Any = None,
        event_dispatcher: Any = None,
    ) -> dict[str, Any]:
        """Execute a workflow step using the unified QueryEngine.

        This method replaces step_runner.run_workflow_step by integrating
        WorkflowStep → DelegationTask conversion and delegation execution
        directly in the QueryEngine.

        Args:
            step: The WorkflowStep to execute
            user_message: The original user message
            provider: The LLM provider
            model: The LLM model
            session_id: The session ID
            folder_path: Working directory for filesystem tools
            memory_context: RAG context from agent history
            memory_grounded: If response should prioritize memory context
            conversation_history: Full conversation history
            prior_context: Context from previous workflow steps
            chunk_dispatcher: Optional chunk dispatcher (not used in current impl)
            event_dispatcher: Optional event dispatcher (not used in current impl)

        Returns:
            Dict with execution results in step_runner format
        """
        # Convert WorkflowStep to DelegationTask
        task = self._workflow_step_to_delegation_task(
            step=step,
            user_message=user_message,
            session_id=session_id,
            memory_context=memory_context,
            memory_grounded=memory_grounded,
            conversation_history=conversation_history,
            prior_context=prior_context,
            folder_path=folder_path,
        )

        # Execute delegation
        # Note: session parameter is optional for delegate_task, passing None
        result = await self.delegate_task(
            task=task,
            session=None,  # OrchestratorSession not needed for workflow steps
            session_id=session_id,
        )

        # Convert DelegationResult back to step_runner format
        return self._delegation_result_to_step_output(result, step)

    def _workflow_step_to_delegation_task(
        self,
        step: WorkflowStep,
        user_message: str,
        session_id: str,
        *,
        memory_context: str = "",
        memory_grounded: bool = False,
        conversation_history: list[dict[str, str]] | None = None,
        prior_context: str = "",
        folder_path: str | None = None,
        max_iterations: int = 1,
    ) -> DelegationTask:
        """Convert WorkflowStep to DelegationTask for execution.

        This is the same logic from orchestrator/delegation/converter.py,
        now integrated directly in QueryEngine.
        """
        return DelegationTask(
            agent=step.agent_role,
            agent_role=step.agent_role,
            specialist=step.specialist,
            agent_id=step.agent_id,
            objective=step.objective or user_message,
            scope=[],  # WorkflowStep doesn't have scope field
            exclusions=[],  # WorkflowStep doesn't have exclusions field
            expected_output="",  # WorkflowStep doesn't have expected_output field
            context_from_session=prior_context,  # Map prior_context to context_from_session
            priority=Priority.NORMAL,  # Default priority
            tools=step.tools,  # Preserve tool scope from step
            root_dir=folder_path,
            max_iterations=max_iterations,
            session_id=session_id,
            # New fields from step_runner integration
            memory_context=memory_context,
            memory_grounded=memory_grounded,
            conversation_history=conversation_history or [],
            streaming_enabled=False,  # Streaming not yet supported
        )

    def _delegation_result_to_step_output(
        self,
        delegation_result: DelegationResult,
        step: WorkflowStep,
    ) -> dict[str, Any]:
        """Convert DelegationResult back to step_runner output format.

        This is the same logic from orchestrator/delegation/converter.py,
        now integrated directly in QueryEngine.
        """
        return {
            "agent_id": step.agent_id,
            "agent_role": step.agent_role.value,
            "specialist": step.specialist.value if step.specialist else None,
            "status": delegation_result.status.value,
            "key_findings": delegation_result.key_findings,
            "full_output": delegation_result.full_output,
            "error": delegation_result.error_message,
        }
