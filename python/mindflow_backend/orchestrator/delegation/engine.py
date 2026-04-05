"""Delegation Engine — Handles agent task execution and result collection.

Manages the actual delegation of tasks to agents, tracks execution,
and returns structured results that the Orchestrator can integrate.
"""

from __future__ import annotations

from typing import Any

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
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.services.core import get_worktree_service
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import (
    SandboxMode,
    WorkspaceBinding,
    WorkspacePolicy,
)

from .execution_helpers import ExecutionMemoryMixin

_logger = get_logger(__name__)


class DelegationEngine(ExecutionMemoryMixin):
    """Handles execution of delegated tasks to specialized agents."""
    
    def __init__(self, *, execution_memory: Any | None = None):
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

    def _register_fallback_handlers(self) -> None:
        """Register fallback handlers for delegation engine."""

        async def delegation_fallback(ctx: FallbackContext) -> DelegationResult:
            """Fallback handler for delegation - return error result."""
            _logger.warning(
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
            _logger.debug("mission_launcher_initialized")
        except Exception:
            _logger.warning("mission_launcher_unavailable")
            self._mission_launcher = None  # Ensure not retried

        return self._mission_launcher

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
            _logger.warning(
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
        
        _logger.info(
            "delegation_started",
            agent=task.agent.value,
            task_id=str(task.task_id),
            objective=task.objective,
        )

        # Fase C: Intercept calls mapped to an external A2A address
        if task.agent_id and task.agent_id.startswith("a2a://"):
            from mindflow_backend.communication.a2a.a2a_client import A2AClient
            _logger.info("delegating_to_a2a_external_agent", target=task.agent_id)
            # The A2A Target URL is basically the agent_id, replacing "a2a://" with "http://" for mapping purposes or kept as original depending on network resolution
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
                _logger.warning(
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

        # Define primary delegation logic
        async def _delegation_primary() -> DelegationResult:
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
                _logger.debug(
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
                    tool_context = ToolContext(
                        permission_context=None,  # TODO: Add permission context
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

                elif strategy == "legacy":
                    # Legacy path: Use LangChain adapter for backward compatibility
                    from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
                    from mindflow_backend.archive.tool_invocation import invoke_with_tools

                    lc_tools = to_langchain_tools(tools)
                    if lc_tools:
                        llm_with_tools = llm.bind_tools(lc_tools)
                        response_text = await invoke_with_tools(
                            llm=llm_with_tools,
                            messages=messages,
                            lc_tools=lc_tools,
                            event_dispatcher=self._make_event_dispatcher(child_execution_id),
                            before_iteration=self._make_before_iteration(child_execution_id),
                            max_iterations=max(1, getattr(task, "max_iterations", 1) * 5),
                            session_id=session_id,
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

            _logger.info(
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

        # Execute with fallback (includes retry logic automatically)
        fallback_result = await self._fallback_manager.execute_with_fallback(
            component="delegation_engine",
            primary_func=_delegation_primary,
            context={"task": task},
        )

        if fallback_result.success:
            result = fallback_result.result
        else:
            # Ultimate fallback if everything fails
            _logger.error(
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

    def _format_task_for_agent(self, task: DelegationTask) -> str:
        """Format the delegation task for the specific agent."""
        
        task_prompt = f"""You are a {task.agent.value} agent. 

OBJECTIVE: {task.objective}

SCOPE: {', '.join(task.scope) if task.scope else 'Determine appropriate scope based on objective'}

EXCLUSIONS: {', '.join(task.exclusions) if task.exclusions else 'None'}

EXPECTED OUTPUT FORMAT: {task.expected_output or 'Provide a complete solution following your agent\'s best practices'}

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
        """Extract key findings from agent response."""
        # For now, return the full response but compressed
        # TODO: Implement smarter extraction based on expected_output
        if len(response) > 1000:
            # Compress long responses
            return response[:500] + "... [truncated for context efficiency]"
        return response
    
    def _extract_files_mentioned(self, response: str) -> list[str]:
        """Extract file paths mentioned in response."""
        import re
        # Simple regex to find file-like patterns
        file_pattern = r'\b[\w\-_\/\.]+\.(py|js|ts|json|yaml|yml|md|txt|sql)\b'
        matches = re.findall(file_pattern, response, re.IGNORECASE)
        return list(set(matches))
    
    def _extract_symbols_mentioned(self, response: str) -> list[str]:
        """Extract function/class/symbol names mentioned in response."""
        import re
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


# Global delegation engine instance
_delegation_engine: DelegationEngine | None = None


def get_delegation_engine() -> DelegationEngine:
    """Get or create the global delegation engine instance."""
    global _delegation_engine
    if _delegation_engine is None:
        _delegation_engine = DelegationEngine()
    return _delegation_engine
