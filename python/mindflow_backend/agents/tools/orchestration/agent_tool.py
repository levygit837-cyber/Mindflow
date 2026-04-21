"""AgentTool — lets the Orchestrator delegate tasks to specialist agents.

Based on Claude Code's AgentTool, this tool replaces delegate_to_agent with a
Claude-style interface while preserving MindFlow's delegation capabilities.

The Orchestrator calls this tool when it needs a specialist (analyst, coder,
researcher, or any registered specialist) to perform work. The tool executes the
agent via the QueryEngine and returns the agent's full output so the Orchestrator
can synthesize and respond to the user.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class AgentTool(AsyncToolInterface):
    """Delegate a task to a specialist agent using Claude-style interface.

    This tool follows Claude Code's AgentTool interface while preserving
    MindFlow's delegation capabilities (context, scope, expected_output, etc.).
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "AgentTool"
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
                    "description": {
                        "type": "string",
                        "description": "A short (3-5 word) description of the task.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The task for the agent to perform.",
                    },
                    "subagent_type": {
                        "type": "string",
                        "description": (
                            "The type of specialized agent to use for this task. "
                            "Examples: 'analyst', 'coder', 'researcher', "
                            "'analyst:security_guard', 'analyst:critic', "
                            "'analyst:brainstorm', 'analyst:deep_iteration', "
                            "'coder:arch_tech'."
                        ),
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "Optional model override for this agent. "
                            "Takes precedence over the agent definition's model. "
                            "If omitted, uses the agent definition's model, "
                            "or inherits from the parent."
                        ),
                    },
                    "run_in_background": {
                        "type": "boolean",
                        "description": (
                            "Set to true to run this agent in the background. "
                            "You will be notified when it completes."
                        ),
                    },
                    "name": {
                        "type": "string",
                        "description": (
                            "Name for the spawned agent. Makes it addressable "
                            "via SendMessage({to: name}) while running."
                        ),
                    },
                    "isolation": {
                        "type": "string",
                        "enum": ["worktree", "remote"],
                        "description": (
                            "Isolation mode. 'worktree' creates a temporary git worktree "
                            "so the agent works on an isolated copy of the repo."
                        ),
                    },
                    # Preserved from delegate_to_agent for backward compatibility
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
                "required": ["description", "prompt"],
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        description: str = kwargs.get("description", "")
        prompt: str = kwargs.get("prompt", "")
        subagent_type: str = kwargs.get("subagent_type", "analyst")
        model: str | None = kwargs.get("model")
        run_in_background: bool | None = kwargs.get("run_in_background")
        name: str | None = kwargs.get("name")
        isolation: str | None = kwargs.get("isolation")
        
        # Preserved from delegate_to_agent
        scope: list[str] = kwargs.get("scope") or []
        context: str = kwargs.get("context") or ""
        expected_output: str = kwargs.get("expected_output") or ""

        if not prompt.strip():
            return "Error: prompt is required and must not be empty."

        _logger.info(
            "agent_tool_invoked",
            subagent_type=subagent_type,
            description=description,
            prompt=prompt[:120],
            scope=scope,
        )

        try:
            from mindflow_backend.query.budget.token_counter import TokenBudget
            from mindflow_backend.query.engine import QueryEngine
            from mindflow_backend.schemas.orchestration.delegation import (
                DelegationTask,
                OrchestratorSession,
            )
            from mindflow_backend.schemas.orchestration.orchestrator import AgentType, WorkspacePolicy

            # Parse subagent_type into agent + specialist (preserved logic)
            specialist = None
            if ":" in subagent_type:
                role_str, specialist_str = subagent_type.split(":", 1)
                from mindflow_backend.schemas.orchestration.specialists import SpecialistType
                try:
                    agent_type = AgentType(role_str.lower())
                    specialist = SpecialistType(specialist_str.lower())
                except ValueError:
                    agent_type = AgentType.ANALYST
            else:
                try:
                    agent_type = AgentType(subagent_type.lower())
                except ValueError:
                    _logger.warning(f"Unknown subagent_type {subagent_type!r}, falling back to analyst")
                    agent_type = AgentType.ANALYST

            # Handle isolation mode (worktree support)
            root_dir = None
            if isolation == "worktree" and self.root_dir:
                root_dir = self.root_dir

            task = DelegationTask(
                agent=agent_type,
                specialist=specialist,
                agent_id=subagent_type,
                objective=prompt,  # Use prompt as objective
                scope=scope,
                context_from_session=context,
                expected_output=expected_output,
                max_iterations=50,  # Increased from 10 to match Claude's default
                root_dir=root_dir,
                workspace_policy=WorkspacePolicy.WORKTREE if root_dir else WorkspacePolicy.AUTO,
            )

            # Inject folder_path into the task context hint if available (preserved logic)
            if root_dir and root_dir not in scope:
                task = task.model_copy(
                    update={
                        "context_from_session": (
                            f"Working directory: {root_dir}\n{context}"
                            if context
                            else f"Working directory: {root_dir}"
                        )
                    }
                )

            engine = QueryEngine(
                providers=[],  # No context providers for delegation
                budget=TokenBudget(max_tokens=200_000),
                session_id=self.session_id,
                use_file_cache=True,
            )
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

            # Return result in Claude-style format
            output = result.full_output or result.key_findings or "Agent completed the task but returned no output."
            
            # If background execution, return agent_id for reference
            if run_in_background:
                return f"Async agent launched successfully.\nagentId: {result.agent_id}\nThe agent is working in the background. You will be notified automatically when it completes."
            
            return output

        except Exception as exc:
            _logger.error(f"agent_tool_error: {exc}")
            return f"Error during delegation: {exc}"
