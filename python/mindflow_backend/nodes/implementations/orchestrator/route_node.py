"""RouteNode — Entry point using QueryLoop (Claude-style)."""

from __future__ import annotations

from typing import Any

from mindflow_backend.nodes.base.node import BaseNode, NodeCategory, NodeType
from mindflow_backend.nodes.base.stateful import StatefulNode


class RouteNode(StatefulNode, BaseNode):
    """Node that executes QueryLoop with Orchestrator (Claude-style).

    This replaces the HybridRouter with a direct QueryLoop that:
      - Executes Orchestrator with AgentTool and SendMessageTool
      - Continues looping while Orchestrator uses AgentTool
      - No LLM routing calls before execution (0 latency overhead)
    """

    def __init__(self, node_id: str = "route") -> None:
        super().__init__(
            node_id=node_id,
            node_type=NodeType.ROUTER,
            category=NodeCategory.CONTROL_FLOW,
            description="Execute QueryLoop with Orchestrator using AgentTool",
        )

        # Required inputs for QueryLoop
        self.config.required_inputs = {"message"}
        self.config.outputs = {"messages", "turn_count"}

    async def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute QueryLoop with Orchestrator."""
        from mindflow_backend.agents._registry import get_agent
        from mindflow_backend.agents.tools import get_default_registry
        from mindflow_backend.infra.logging import get_logger
        from mindflow_backend.query.budget.token_counter import TokenBudget
        from mindflow_backend.query.query_loop import query_loop

        _logger = get_logger(__name__)
        session_id = state.get("session_id")
        execution_id = state.get("execution_id")
        folder_path = state.get("folder_path")

        _logger.info(
            "route_node_starting_queryloop",
            message=state["message"][:100],
            has_folder_path=bool(folder_path),
        )

        try:
            # Get Orchestrator agent
            orchestrator = get_agent("orchestrator", session_id=session_id)

            # Get tools (AgentTool + SendMessageTool)
            tools = get_default_registry().get_tools_for_scope("delegation")

            # Set root_dir on tools if folder_path provided
            if folder_path:
                for tool in tools:
                    if hasattr(tool, "root_dir"):
                        tool.root_dir = folder_path
                    if session_id and hasattr(tool, "session_id"):
                        tool.session_id = session_id
                    if execution_id and hasattr(tool, "execution_id"):
                        tool.execution_id = execution_id

            # Execute QueryLoop
            messages = []
            turn_count = 0

            async for message in query_loop(
                initial_message=state["message"],
                orchestrator=orchestrator,
                tools=tools,
                max_turns=50,
                token_budget=TokenBudget(max_tokens=200_000),
                session_id=session_id,
                execution_id=execution_id,
            ):
                messages.append(message)
                turn_count += 1

            _logger.info(
                "route_node_queryloop_completed",
                turn_count=turn_count,
                message_count=len(messages),
            )

            self.set_node_state("last_turn_count", turn_count)
            self.set_node_state("routing_count", self.get_node_state("routing_count", 0) + 1)

            return {
                "messages": messages,
                "turn_count": turn_count,
            }

        except Exception as exc:
            _logger.error("route_node_queryloop_error", error=str(exc), exc_info=True)
            # Fallback: return error message
            return {
                "messages": [
                    {
                        "type": "system",
                        "content": f"QueryLoop error: {exc}",
                    }
                ],
                "turn_count": 0,
            }

    def validate_inputs(self, state: dict[str, Any]) -> list[str]:
        """Validate routing inputs."""
        errors = []

        if "message" not in state:
            errors.append("Missing required input: message")
        elif not isinstance(state["message"], str) or not state["message"].strip():
            errors.append("Message must be a non-empty string")

        return errors

    async def _on_initialize(self) -> None:
        """Initialize the route node."""
        self.set_node_state("routing_count", 0)
        self.set_node_state("last_agent", None)
        self.set_node_state("last_complexity", 0.0)

