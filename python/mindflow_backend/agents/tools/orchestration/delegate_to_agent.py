"""DelegateToAgentTool — lets the Orchestrator delegate tasks to specialist agents.

The Orchestrator calls this tool when it needs a specialist (analyst, coder,
researcher, or any registered specialist) to perform work. The tool executes the
agent via the DelegationEngine and returns the agent's full output as a string so
the Orchestrator can synthesize and respond to the user.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class DelegateToAgentTool(AsyncToolInterface):
    """Delegate a task to a specialist agent and return its complete response."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "delegate_to_agent"
        self.description = (
            "Delegate a task to a specialist agent (analyst, coder, researcher, "
            "analyst:security_guard, analyst:critic, analyst:brainstorm, "
            "analyst:deep_iteration, coder:arch_tech, etc.). "
            "Returns the agent's complete response as a string. "
            "Use this when the user's request requires code investigation, "
            "implementation, research, or any task beyond your direct knowledge."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": (
                            "Which agent to delegate to. "
                            "Examples: 'analyst', 'coder', 'researcher', "
                            "'analyst:security_guard', 'analyst:critic', "
                            "'analyst:brainstorm', 'analyst:deep_iteration', "
                            "'coder:arch_tech'."
                        ),
                    },
                    "objective": {
                        "type": "string",
                        "description": "One clear sentence describing what the agent must accomplish.",
                    },
                    "scope": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "List of files or areas to focus on. "
                            "Empty means the agent decides its own scope."
                        ),
                        "default": [],
                    },
                    "context": {
                        "type": "string",
                        "description": (
                            "Compressed relevant background from the conversation "
                            "that the agent needs to know."
                        ),
                        "default": "",
                    },
                    "expected_output": {
                        "type": "string",
                        "description": (
                            "What structure or format you expect back from the agent. "
                            "e.g., 'Return a list of public functions with signatures.'"
                        ),
                        "default": "",
                    },
                },
                "required": ["agent_id", "objective"],
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        agent_id: str = kwargs.get("agent_id", "analyst")
        objective: str = kwargs.get("objective", "")
        scope: list[str] = kwargs.get("scope") or []
        context: str = kwargs.get("context") or ""
        expected_output: str = kwargs.get("expected_output") or ""

        if not objective.strip():
            return "Error: objective is required and must not be empty."

        _logger.info(
            "delegate_to_agent_tool_invoked",
            agent_id=agent_id,
            objective=objective[:120],
            scope=scope,
        )

        try:
            from mindflow_backend.orchestrator.delegation.engine import DelegationEngine
            from mindflow_backend.schemas.orchestration.delegation import (
                DelegationTask,
                OrchestratorSession,
            )
            from mindflow_backend.schemas.orchestration.orchestrator import AgentType

            # Parse agent_id into agent + specialist
            specialist = None
            if ":" in agent_id:
                role_str, specialist_str = agent_id.split(":", 1)
                from mindflow_backend.schemas.orchestration.specialists import SpecialistType
                try:
                    agent_type = AgentType(role_str.lower())
                    specialist = SpecialistType(specialist_str.lower())
                except ValueError:
                    agent_type = AgentType.ANALYST
            else:
                try:
                    agent_type = AgentType(agent_id.lower())
                except ValueError:
                    _logger.warning(f"Unknown agent_id {agent_id!r}, falling back to analyst")
                    agent_type = AgentType.ANALYST

            task = DelegationTask(
                agent=agent_type,
                specialist=specialist,
                agent_id=agent_id,
                objective=objective,
                scope=scope,
                context_from_session=context,
                expected_output=expected_output,
                max_iterations=10,
                root_dir=self.root_dir or None,
            )

            # Inject folder_path into the task context hint if available
            if self.root_dir and self.root_dir not in scope:
                task = task.model_copy(
                    update={
                        "context_from_session": (
                            f"Working directory: {self.root_dir}\n{context}"
                            if context
                            else f"Working directory: {self.root_dir}"
                        )
                    }
                )

            engine = DelegationEngine()
            session = OrchestratorSession()
            result = await engine.delegate_task(
                task,
                session,
                session_id=self.session_id,
                root_execution_id=self.execution_id,
                parent_execution_id=self.execution_id,
            )

            if result.status == "failed":
                return f"Delegation failed: {result.error_message}"

            return result.full_output or result.key_findings or "Agent completed the task but returned no output."

        except Exception as exc:
            _logger.error(f"delegate_to_agent_tool_error: {exc}")
            return f"Error during delegation: {exc}"
