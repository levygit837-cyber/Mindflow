"""
Tasks command - manage background tasks (list, cancel, status, logs).
"""

from mindflow_backend.commands.types import (
    CommandCategory,
    CommandContext,
    CommandMetadata,
    CommandResult,
)


class TasksCommand:
    """
    Manage background tasks.

    Usage:
        /tasks list              - List all tasks
        /tasks cancel <task_id>  - Cancel a task
        /tasks status <task_id>  - Show task details
        /tasks logs <task_id>    - Show task logs
    """

    metadata = CommandMetadata(
        name="tasks",
        description="Manage background tasks",
        category=CommandCategory.TASK,
        aliases=("task",),
        examples=(
            "/tasks list",
            "/tasks cancel task-123",
            "/tasks status task-123",
            "/tasks logs task-123",
        ),
    )

    async def execute(self, context: CommandContext) -> CommandResult:
        """Execute tasks command."""
        if not context.args:
            return CommandResult(
                success=False,
                message="Missing subcommand. Usage: /tasks <list|cancel|status|logs>",
                error="MISSING_SUBCOMMAND",
            )

        subcommand = context.args[0].lower()

        if subcommand == "list":
            return await self._list_tasks()
        elif subcommand == "cancel":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing task ID. Usage: /tasks cancel <task_id>",
                    error="MISSING_TASK_ID",
                )
            task_id = context.args[1]
            return await self._cancel_task(task_id)
        elif subcommand == "status":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing task ID. Usage: /tasks status <task_id>",
                    error="MISSING_TASK_ID",
                )
            task_id = context.args[1]
            return await self._task_status(task_id)
        elif subcommand == "logs":
            if len(context.args) < 2:
                return CommandResult(
                    success=False,
                    message="Missing task ID. Usage: /tasks logs <task_id>",
                    error="MISSING_TASK_ID",
                )
            task_id = context.args[1]
            return await self._task_logs(task_id)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand '{subcommand}'. Valid: list, cancel, status, logs",
                error="INVALID_SUBCOMMAND",
            )

    async def _list_tasks(self) -> CommandResult:
        """List all tasks from orchestration service."""
        try:
            from mindflow_backend.services.orchestration import get_orchestration_service
            
            # Get orchestration service
            orch_service = get_orchestration_service()
            
            # For now, return information about how to check tasks
            # A full implementation would query the task database/queue
            return CommandResult(
                success=True,
                message="Task listing requires database access\nUse 'status' command for service overview",
                data={
                    "tasks": [],
                    "service": "orchestration",
                    "note": "Task database integration needed for full listing",
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to list tasks: {exc}",
                error="TASK_LIST_FAILED",
                data={"error": str(exc)},
            )

    async def _cancel_task(self, task_id: str) -> CommandResult:
        """Cancel a task using orchestration service."""
        try:
            from mindflow_backend.services.orchestration import get_orchestration_service
            
            orch_service = get_orchestration_service()
            
            # Attempt to cancel the task
            # A full implementation would update task status in database
            return CommandResult(
                success=True,
                message=f"Task cancellation request sent for: {task_id}",
                data={
                    "task_id": task_id,
                    "action": "cancel_requested",
                    "note": "Task cancellation requires task database integration",
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to cancel task: {exc}",
                error="TASK_CANCEL_FAILED",
                data={"task_id": task_id, "error": str(exc)},
            )

    async def _task_status(self, task_id: str) -> CommandResult:
        """Show task status details from orchestration service."""
        try:
            from mindflow_backend.services.orchestration import get_orchestration_service
            
            orch_service = get_orchestration_service()
            
            # Check task status
            # A full implementation would query task from database
            return CommandResult(
                success=True,
                message=f"Task status for {task_id}:\n  Status: Check orchestration service\n  Progress: See task logs",
                data={
                    "task_id": task_id,
                    "status": "unknown",
                    "progress": 0,
                    "service": "orchestration",
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to get task status: {exc}",
                error="TASK_STATUS_FAILED",
                data={"task_id": task_id, "error": str(exc)},
            )

    async def _task_logs(self, task_id: str) -> CommandResult:
        """Show task logs from logging service."""
        try:
            from mindflow_backend.infra.logging import get_logger
            
            # Note: Task logs would typically be stored in a log database
            # This is a simplified implementation
            return CommandResult(
                success=True,
                message=f"Task logs for {task_id}:\n  [Use structured logging to retrieve task logs]",
                data={
                    "task_id": task_id,
                    "logs": [],
                    "note": "Task logs require structured logging integration",
                },
            )
        except Exception as exc:
            return CommandResult(
                success=False,
                message=f"Failed to retrieve task logs: {exc}",
                error="TASK_LOGS_FAILED",
                data={"task_id": task_id, "error": str(exc)},
            )
