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
        """Show agent status."""
        # TODO: Integrate with actual agent system when available
        # For now, return stub data
        return CommandResult(
            success=True,
            message="  Active agents: 0\n  Total spawned: 0",
            data={
                "active_count": 0,
                "total_spawned": 0,
            },
        )

    async def _show_task_status(self) -> CommandResult:
        """Show task status."""
        # TODO: Integrate with Phase 2 task system when available
        # For now, return stub data
        return CommandResult(
            success=True,
            message="  Running tasks: 0\n  Queued tasks: 0\n  Completed tasks: 0",
            data={
                "running": 0,
                "queued": 0,
                "completed": 0,
            },
        )

    async def _show_memory_status(self) -> CommandResult:
        """Show memory status."""
        # TODO: Integrate with actual memory service
        # For now, return stub data
        return CommandResult(
            success=True,
            message="  Total entries: 0\n  Cache size: 0 MB\n  Sessions: 0",
            data={
                "total_entries": 0,
                "cache_size_mb": 0,
                "sessions": 0,
            },
        )

    async def _show_service_status(self) -> CommandResult:
        """Show service health status."""
        # TODO: Integrate with actual service health checks
        # For now, return stub data
        services = {
            "postgresql": "unknown",
            "rabbitmq": "unknown",
            "redis": "unknown",
        }

        lines = []
        for service, status in services.items():
            lines.append(f"  {service}: {status}")

        return CommandResult(
            success=True,
            message="\n".join(lines),
            data={"services": services},
        )
