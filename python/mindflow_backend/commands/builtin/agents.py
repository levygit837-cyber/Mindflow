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
        """List all active agents using AgentTeamManager."""
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            
            team_manager = AgentTeamManager()
            
            # Get active team sessions
            active_teams = []
            for team_id, team_data in team_manager._teams.items():
                active_teams.append({
                    "team_id": str(team_id),
                    "agents": team_data.get("agent_ids", []),
                    "created_at": team_data.get("created_at", "unknown"),
                    "task_preview": team_data.get("task", "")[:100],
                })
            
            if active_teams:
                message_lines = [f"Active agent teams: {len(active_teams)}", ""]
                for team in active_teams:
                    message_lines.append(f"Team {team['team_id'][:8]}:")
                    message_lines.append(f"  Agents: {', '.join(team['agents'])}")
                    message_lines.append(f"  Task: {team['task_preview']}...")
                    message_lines.append("")
                
                return CommandResult(
                    success=True,
                    message="\n".join(message_lines),
                    data={"teams": active_teams, "total_agents": sum(len(t['agents']) for t in active_teams)},
                )
            else:
                return CommandResult(
                    success=True,
                    message="Active agents: 0\n\nNo agents currently running",
                    data={"agents": [], "teams": []},
                )
                
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to list agents: {exc}",
                error="AGENT_LIST_FAILED",
                data={"error": str(exc)},
            )

    async def _spawn_agent(
        self, agent_type: str, context: CommandContext
    ) -> CommandResult:
        """Spawn a new agent via team manager."""
        valid_types = ["planner", "reviewer", "explorer", "tester", "general", "coder", "analyst", "researcher"]

        if agent_type not in valid_types:
            return CommandResult(
                success=False,
                message=f"Invalid agent type '{agent_type}'. Valid types: {', '.join(valid_types)}",
                error="INVALID_AGENT_TYPE",
            )

        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            import uuid
            
            team_manager = AgentTeamManager()
            session_id = f"cli_spawn_{uuid.uuid4().hex[:8]}"
            
            # Create a simple task for the agent
            task = f"CLI spawned {agent_type} agent ready for commands"
            
            # Run team session with single agent
            result = await team_manager.run_team_session(
                task=task,
                agent_ids=[agent_type],
                session_id=session_id,
                skip_discussion=True,
            )
            
            if result.success:
                return CommandResult(
                    success=True,
                    message=f"Agent '{agent_type}' spawned successfully (Team: {result.team_id[:8]})",
                    data={
                        "agent_type": agent_type,
                        "team_id": result.team_id,
                        "session_id": session_id,
                        "status": "active",
                    },
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"Agent spawn failed: {result.synthesized_response or 'Unknown error'}",
                    error="SPAWN_FAILED",
                    data={"agent_type": agent_type, "error": result.synthesized_response},
                )
                
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Agent spawn error: {exc}",
                error="SPAWN_ERROR",
                data={"agent_type": agent_type, "error": str(exc)},
            )

    async def _kill_agent(self, agent_id: str) -> CommandResult:
        """Terminate an agent team session."""
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            
            team_manager = AgentTeamManager()
            
            # Try to find and terminate the team
            if agent_id in team_manager._teams:
                del team_manager._teams[agent_id]
                return CommandResult(
                    success=True,
                    message=f"Agent team '{agent_id[:8]}' terminated successfully",
                    data={"agent_id": agent_id, "action": "terminated"},
                )
            else:
                return CommandResult(
                    success=False,
                    message=f"Agent team '{agent_id}' not found. Use 'agents list' to see active agents.",
                    error="AGENT_NOT_FOUND",
                    data={"agent_id": agent_id},
                )
                
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to kill agent: {exc}",
                error="KILL_FAILED",
                data={"agent_id": agent_id, "error": str(exc)},
            )

    async def _agent_status(self, agent_id: str) -> CommandResult:
        """Show agent team status details."""
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            
            team_manager = AgentTeamManager()
            
            if agent_id not in team_manager._teams:
                return CommandResult(
                    success=False,
                    message=f"Agent team '{agent_id}' not found",
                    error="AGENT_NOT_FOUND",
                    data={"agent_id": agent_id},
                )
            
            team_data = team_manager._teams[agent_id]
            
            status_lines = [
                f"Agent Team: {agent_id[:8]}",
                f"Status: Active",
                f"Agents: {', '.join(team_data.get('agent_ids', []))}",
                f"Created: {team_data.get('created_at', 'unknown')}",
                f"Task: {team_data.get('task', 'N/A')[:150]}...",
            ]
            
            return CommandResult(
                success=True,
                message="\n".join(status_lines),
                data={
                    "agent_id": agent_id,
                    "agents": team_data.get("agent_ids", []),
                    "task": team_data.get("task", ""),
                    "status": "active",
                },
            )
                
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to get agent status: {exc}",
                error="STATUS_FAILED",
                data={"agent_id": agent_id, "error": str(exc)},
            )
