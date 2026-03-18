"""Delegation Engine — Handles agent task execution and result collection.

Manages the actual delegation of tasks to agents, tracks execution,
and returns structured results that the Orchestrator can integrate.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents._registry import get_agent
from mindflow_backend.agents.tools import create_default_registry
from mindflow_backend.agents.tools.sandbox import MindFlowSandbox
from mindflow_backend.execution_memory import get_execution_memory_service
from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.runtime.providers import get_model_for_provider
from mindflow_backend.schemas.orchestration.delegation import DelegationResult, DelegationTask
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode

_logger = get_logger(__name__)


class DelegationEngine:
    """Handles execution of delegated tasks to specialized agents."""
    
    def __init__(self, *, execution_memory: Any | None = None):
        self.settings = get_settings()
        self._execution_memory = execution_memory or get_execution_memory_service()
        
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

        child_execution = await self._start_child_execution(
            task=task,
            session_id=session_id,
            root_execution_id=root_execution_id,
            parent_execution_id=parent_execution_id,
        )
        child_execution_id = getattr(child_execution, "id", None)
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
        
        try:
            # Get the target agent
            agent = get_agent(task.agent_role or task.agent, specialist=task.specialist, agent_id=task.agent_id)
            
            # Prepare messages for the agent
            messages = [
                {"role": "system", "content": agent.system_prompt}
            ]
            
            # Add context if provided
            if task.context_from_session:
                messages.append(
                    {"role": "system", "content": f"Relevant context from previous delegations:\n{task.context_from_session}"}
                )
            
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
                from mindflow_backend.agents.tools.orchestration.notify_orchestrator import NotifyOrchestratorTool

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
            if tools:
                from mindflow_backend.agents.tools.base.langchain_adapter import to_langchain_tools
                from mindflow_backend.agents.tools.base.tool_invocation import invoke_with_tools

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
            
        except Exception as exc:
            _logger.error(
                "delegation_failed",
                agent=task.agent.value,
                task_id=str(task.task_id),
                error=str(exc),
            )

            if child_execution_id:
                await self._append_execution_event(
                    child_execution_id,
                    "delegation_failed",
                    {
                        "task_id": str(task.task_id),
                        "error": str(exc),
                        "success": False,
                    },
                    stage="finalizing",
                )
                await self._mark_execution_status(
                    child_execution_id,
                    "failed",
                    stage="finalizing",
                    error=str(exc),
                )
            
            return DelegationResult(
                task_id=task.task_id,
                agent=task.agent,
                agent_role=task.agent_role or task.agent,
                specialist=task.specialist,
                agent_id=task.agent_id,
                status="failed",
                key_findings="",
                full_output="",
                confidence=0.0,
                tokens_consumed=0,
                error_message=str(exc),
            )

    async def _start_child_execution(
        self,
        *,
        task: DelegationTask,
        session_id: str | None,
        root_execution_id: str | None,
        parent_execution_id: str | None,
    ) -> Any | None:
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
                },
            )
        except Exception as exc:
            _logger.warning("delegation_child_execution_start_failed", error=str(exc))
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
            _logger.warning("delegation_event_persist_failed", execution_id=execution_id, error=str(exc))

    async def _mark_execution_status(
        self,
        execution_id: str | None,
        status: str,
        **updates: Any,
    ) -> None:
        if self._execution_memory is None or not execution_id:
            return
        try:
            await self._execution_memory.mark_status(execution_id, status, **updates)
        except Exception as exc:
            _logger.warning("delegation_status_persist_failed", execution_id=execution_id, error=str(exc))

    async def _record_result_message(
        self,
        *,
        child_execution_id: str,
        recipient_execution_id: str | None,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
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
            _logger.warning("delegation_message_persist_failed", execution_id=child_execution_id, error=str(exc))

    def _make_event_dispatcher(self, execution_id: str | None):
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
        async def _before_iteration(messages: list[Any], _iteration: int) -> None:
            if self._execution_memory is None or not execution_id:
                return

            try:
                pending = await self._execution_memory.consume_pending_messages(execution_id=execution_id)
            except Exception as exc:
                _logger.warning("delegation_pending_message_load_failed", execution_id=execution_id, error=str(exc))
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
                await self._mark_execution_status(execution_id, "running", stage="working")

        return _before_iteration
    
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


# Global delegation engine instance
_delegation_engine: DelegationEngine | None = None


def get_delegation_engine() -> DelegationEngine:
    """Get or create the global delegation engine instance."""
    global _delegation_engine
    if _delegation_engine is None:
        _delegation_engine = DelegationEngine()
    return _delegation_engine
