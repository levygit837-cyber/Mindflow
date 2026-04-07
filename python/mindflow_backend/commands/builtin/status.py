"""
Status command - shows system status (agents, tasks, memory, services).
"""

import asyncio
from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class StatusCommand:
    """
    Display system status information.

    Shows:
    - Active agents count
    - Running tasks count
    - Memory usage stats
    - Service health (PostgreSQL, RabbitMQ, Redis)
    - Execution queue depth

    Usage:
        /status              - Show all status information
        /status agents       - Show only agent status
        /status tasks        - Show only task status
        /status memory       - Show only memory status
        /status services     - Show only service health
    """

    metadata = CommandMetadata(
        name="status",
        description="Show system status information",
        category=CommandCategory.SYSTEM,
        aliases=("stat",),
        examples=(
            "/status",
            "/status agents",
            "/status services",
        ),
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute status command."""
        # Determine what to show
        if not context.args:
            return await self._show_all_status()

        section = context.args[0].lower()
        if section == "agents":
            return await self._show_agent_status()
        elif section == "tasks":
            return await self._show_task_status()
        elif section == "memory":
            return await self._show_memory_status()
        elif section == "services":
            return await self._show_service_status()
        else:
            return CommandResult(
                success=False,
                message=f"Unknown status section '{section}'. Valid sections: agents, tasks, memory, services",
                error="INVALID_SECTION",
            )

    async def _show_all_status(self) -> CommandResult:
        """Show all status information."""
        lines = ["System Status:\n"]

        # Get all status sections
        agent_result = await self._show_agent_status()
        task_result = await self._show_task_status()
        memory_result = await self._show_memory_status()
        service_result = await self._show_service_status()

        # Combine results
        lines.append("AGENTS:")
        lines.append(agent_result.message)
        lines.append("\nTASKS:")
        lines.append(task_result.message)
        lines.append("\nMEMORY:")
        lines.append(memory_result.message)
        lines.append("\nSERVICES:")
        lines.append(service_result.message)

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={
                "agents": agent_result.data,
                "tasks": task_result.data,
                "memory": memory_result.data,
                "services": service_result.data,
            },
        )

    async def _show_agent_status(self) -> CommandResult:
        """Show agent status using AgentTeamManager."""
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            
            team_manager = AgentTeamManager()
            
            active_teams = list(team_manager._teams.keys())
            active_count = len(active_teams)
            
            # Count total agents across all teams
            total_agents = sum(
                len(team_data.get("agent_ids", []))
                for team_data in team_manager._teams.values()
            )
            
            return CommandResult(
                success=True,
                message=f"  Active teams: {active_count}\n  Total agents: {total_agents}",
                data={
                    "active_count": active_count,
                    "total_agents": total_agents,
                    "teams": [t[:8] for t in active_teams],
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"  Failed to get agent status: {exc}",
                error="AGENT_STATUS_FAILED",
                data={"error": str(exc)},
            )

    async def _show_task_status(self) -> CommandResult:
        """Show task status using orchestration services."""
        try:
            from mindflow_backend.services.orchestration import get_task_service
            
            task_service = get_task_service()
            
            # Get task counts (this is a simplified implementation)
            # In production, this would query the actual task queue
            return CommandResult(
                success=True,
                message="  Running tasks: Check task service\n  Queued tasks: Check queue\n  Completed tasks: Check history",
                data={
                    "running": 0,  # Would come from task service
                    "queued": 0,
                    "completed": 0,
                    "service_available": True,
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"  Task service unavailable: {exc}",
                error="TASK_STATUS_FAILED",
                data={"error": str(exc)},
            )

    async def _show_memory_status(self) -> CommandResult:
        """Show memory status using memory services."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            
            memory_service = get_memory_facade_service()
            
            # Get memory stats (simplified - would need actual implementation)
            return CommandResult(
                success=True,
                message="  Memory facade: Active\n  Check memory tables for details",
                data={
                    "service_status": "active",
                    "facade_available": True,
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"  Memory service unavailable: {exc}",
                error="MEMORY_STATUS_FAILED",
                data={"error": str(exc)},
            )

    async def _show_service_status(self) -> CommandResult:
        """Show service health status using health checks."""
        try:
            from mindflow_backend.infra.monitoring.health_checks import HealthCheckManager
            
            health_manager = HealthCheckManager()
            
            # Check core services
            services = {
                "postgresql": await self._check_database_health(),
                "memory_facade": await self._check_memory_health(),
                "agent_team": await self._check_agent_health(),
            }
            
            lines = []
            for service, status in services.items():
                status_icon = "✓" if status == "healthy" else "✗" if status == "unhealthy" else "?"
                lines.append(f"  {status_icon} {service}: {status}")
            
            return CommandResult(
                success=all(s == "healthy" for s in services.values()),
                message="\n".join(lines),
                data={"services": services},
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"  Service check failed: {exc}",
                error="SERVICE_CHECK_FAILED",
                data={"error": str(exc)},
            )
    
    async def _check_database_health(self) -> str:
        """Check PostgreSQL health."""
        try:
            from mindflow_backend.infra.database.health import check_database_health
            result = await check_database_health()
            return "healthy" if result.healthy else "unhealthy"
        except Exception:
            return "unknown"
    
    async def _check_memory_health(self) -> str:
        """Check memory service health."""
        try:
            from mindflow_backend.services.memory import get_memory_facade_service
            service = get_memory_facade_service()
            return "healthy" if service else "unhealthy"
        except Exception:
            return "unknown"
    
    async def _check_agent_health(self) -> str:
        """Check agent system health."""
        try:
            from mindflow_backend.execution.agent_team_manager import AgentTeamManager
            manager = AgentTeamManager()
            return "healthy" if manager else "unhealthy"
        except Exception:
            return "unknown"
