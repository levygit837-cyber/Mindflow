"""
Agents command - manage agent lifecycle (list, spawn, kill, status).
"""

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class AgentsCommand:
    """
    Manage agents (list, spawn, kill, status).

    Usage:
        /agents list              - List all active agents
        /agents spawn <type>      - Spawn a new agent of specified type
        /agents kill <agent_id>   - Terminate an agent
        /agents status <agent_id> - Show agent details
    """

    metadata = CommandMetadata(
        name="agents",
        description="Manage agent lifecycle",
        category=CommandCategory.AGENT,
        aliases=("agent",),
        examples=(
            "/agents list",
            "/agents spawn planner",
            "/agents kill agent-123",
            "/agents status agent-123",
        ),
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute agents command."""
        if not context.args:
            return CommandResult(
                success=False,
                message="Missing subcommand. Usage: /agents <list|spawn|kill|status>",
                error="MISSING_SUBCOMMAND",
            )

        subcommand = context.args[0].lower()

        if subcommand == "list":
            return await self._list_agents()
        elif subcommand == "spawn":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing agent type. Usage: /agents spawn <type>",
                    error="MISSING_AGENT_TYPE",
                )
            agent_type = context.args[1]
            return await self._spawn_agent(agent_type, context)
        elif subcommand == "kill":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing agent ID. Usage: /agents kill <agent_id>",
                    error="MISSING_AGENT_ID",
                )
            agent_id = context.args[1]
            return await self._kill_agent(agent_id)
        elif subcommand == "status":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing agent ID. Usage: /agents status <agent_id>",
                    error="MISSING_AGENT_ID",
                )
            agent_id = context.args[1]
            return await self._agent_status(agent_id)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand '{subcommand}'. Valid: list, spawn, kill, status",
                error="INVALID_SUBCOMMAND",
            )

    async def _list_agents(self) -> CommandResult:
        """List all active agents."""
        # TODO: Integrate with Phase 3.3 agent monitor
        # For now, return stub data
        return CommandResult(
            success=True,
            message="Active agents: 0\n\nNo agents currently running",
            data={"agents": []},
        )

    async def _spawn_agent(
        self, agent_type: str, context: CommandContext
    ) -> CommandResult:
        """Spawn a new agent."""
        # TODO: Integrate with Phase 3.3 agent spawner
        # For now, return stub response
        valid_types = ["planner", "reviewer", "explorer", "tester", "general"]

        if agent_type not in valid_types:
            return CommandResult(
                success=False,
                message=f"Invalid agent type '{agent_type}'. Valid types: {', '.join(valid_types)}",
                error="INVALID_AGENT_TYPE",
            )

        return CommandResult(
            success=False,
            message=f"Agent spawning not yet implemented. Type: {agent_type}",
            error="NOT_IMPLEMENTED",
            data={"agent_type": agent_type},
        )

    async def _kill_agent(self, agent_id: str) -> CommandResult:
        """Terminate an agent."""
        # TODO: Integrate with Phase 3.3 agent monitor
        # For now, return stub response
        return CommandResult(
            success=False,
            message=f"Agent termination not yet implemented. Agent ID: {agent_id}",
            error="NOT_IMPLEMENTED",
            data={"agent_id": agent_id},
        )

    async def _agent_status(self, agent_id: str) -> CommandResult:
        """Show agent status details."""
        # TODO: Integrate with Phase 3.3 agent monitor
        # For now, return stub response
        return CommandResult(
            success=False,
            message=f"Agent status not yet implemented. Agent ID: {agent_id}",
            error="NOT_IMPLEMENTED",
            data={"agent_id": agent_id},
        )
