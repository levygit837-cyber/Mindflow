"""Task management tools for agents.

Provides tools for creating, updating, retrieving, and listing tasks
within the task management system.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.exceptions.tasks import (
    CircularDependencyError,
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskVersionConflictError,
)
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tasks import TaskCreate, TaskUpdate
from mindflow_backend.services.orchestration import get_task_management_service

_logger = get_logger(__name__)


class TaskCreateTool(AsyncToolInterface):
    """Create a new task in the task management system."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "task_create"
        self.description = (
            "Create a new task with a subject, description, and optional metadata. "
            "Tasks are automatically assigned sequential IDs within their task list. "
            "You can specify dependencies (blocks/blocked_by) and an owner."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task_list_id": {
                        "type": "string",
                        "description": "Identifier for the task list (e.g., 'session_123', 'project_abc')",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Brief task title (max 256 characters)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description",
                        "default": "",
                    },
                    "active_form": {
                        "type": "string",
                        "description": "Present continuous form for UI display (e.g., 'Running tests')",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Task owner identifier (agent name or user ID)",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked", "failed"],
                        "description": "Initial task status",
                        "default": "pending",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional task metadata as JSON",
                        "default": {},
                    },
                    "blocks": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of task IDs that this task blocks",
                        "default": [],
                    },
                    "blocked_by": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of task IDs that block this task",
                        "default": [],
                    },
                },
                "required": ["task_list_id", "subject"],
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Create a new task.

        Args:
            **kwargs: Task creation parameters

        Returns:
            Dictionary with task data or error
        """
        try:
            task_data = TaskCreate(**kwargs)
            service = get_task_management_service()

            session_id = kwargs.get("session_id")
            task_response = await service.create_task(task_data, session_id=session_id)

            _logger.info(
                "task_created",
                task_id=task_response.id,
                task_list_id=task_response.task_list_id,
                subject=task_response.subject,
            )

            return {
                "success": True,
                "task": task_response.model_dump(),
            }

        except CircularDependencyError as e:
            _logger.warning("circular_dependency_detected", error=str(e))
            return {
                "success": False,
                "error": f"Circular dependency detected: {e}",
                "error_type": "circular_dependency",
            }
        except Exception as e:
            _logger.error("task_create_failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"Failed to create task: {e}",
                "error_type": "unknown",
            }


class TaskUpdateTool(AsyncToolInterface):
    """Update an existing task."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "task_update"
        self.description = (
            "Update an existing task's properties. Supports optimistic locking "
            "via version field. Can update status, subject, description, owner, "
            "metadata, and dependencies."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to update",
                    },
                    "subject": {
                        "type": "string",
                        "description": "New task subject",
                    },
                    "description": {
                        "type": "string",
                        "description": "New task description",
                    },
                    "active_form": {
                        "type": "string",
                        "description": "New active form text",
                    },
                    "owner": {
                        "type": "string",
                        "description": "New task owner",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked", "failed"],
                        "description": "New task status",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "New metadata (replaces existing)",
                    },
                    "add_blocks": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Task IDs to add to blocks list",
                        "default": [],
                    },
                    "add_blocked_by": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Task IDs to add to blocked_by list",
                        "default": [],
                    },
                    "remove_blocks": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Task IDs to remove from blocks list",
                        "default": [],
                    },
                    "remove_blocked_by": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Task IDs to remove from blocked_by list",
                        "default": [],
                    },
                    "version": {
                        "type": "integer",
                        "description": "Current version for optimistic locking",
                    },
                },
                "required": ["task_id"],
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Update a task.

        Args:
            **kwargs: Task update parameters

        Returns:
            Dictionary with updated task data or error
        """
        try:
            task_id = kwargs.pop("task_id")
            session_id = kwargs.pop("session_id", None)
            task_update = TaskUpdate(**kwargs)
            service = get_task_management_service()

            task_response = await service.update_task(task_id, task_update, session_id=session_id)

            _logger.info(
                "task_updated",
                task_id=task_response.id,
                status=task_response.status,
                version=task_response.version,
            )

            return {
                "success": True,
                "task": task_response.model_dump(),
            }

        except TaskNotFoundError as e:
            _logger.warning("task_not_found", task_id=kwargs.get("task_id"), error=str(e))
            return {
                "success": False,
                "error": f"Task not found: {e}",
                "error_type": "not_found",
            }
        except TaskVersionConflictError as e:
            _logger.warning("task_version_conflict", error=str(e))
            return {
                "success": False,
                "error": f"Version conflict: {e}",
                "error_type": "version_conflict",
            }
        except InvalidStatusTransitionError as e:
            _logger.warning("invalid_status_transition", error=str(e))
            return {
                "success": False,
                "error": f"Invalid status transition: {e}",
                "error_type": "invalid_transition",
            }
        except CircularDependencyError as e:
            _logger.warning("circular_dependency_detected", error=str(e))
            return {
                "success": False,
                "error": f"Circular dependency detected: {e}",
                "error_type": "circular_dependency",
            }
        except Exception as e:
            _logger.error("task_update_failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update task: {e}",
                "error_type": "unknown",
            }


class TaskGetTool(AsyncToolInterface):
    """Retrieve a task by ID."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "task_get"
        self.description = (
            "Retrieve a task by its ID. Returns the task with all its properties "
            "including dependencies (blocks/blocked_by lists)."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "ID of the task to retrieve",
                    },
                },
                "required": ["task_id"],
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Retrieve a task.

        Args:
            **kwargs: Must contain task_id

        Returns:
            Dictionary with task data or error
        """
        try:
            task_id = kwargs["task_id"]
            service = get_task_management_service()

            task_response = await service.get_task(task_id)

            return {
                "success": True,
                "task": task_response.model_dump(),
            }

        except TaskNotFoundError as e:
            _logger.warning("task_not_found", task_id=kwargs.get("task_id"), error=str(e))
            return {
                "success": False,
                "error": f"Task not found: {e}",
                "error_type": "not_found",
            }
        except Exception as e:
            _logger.error("task_get_failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"Failed to retrieve task: {e}",
                "error_type": "unknown",
            }


class TaskListTool(AsyncToolInterface):
    """List tasks with optional filters."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "task_list"
        self.description = (
            "List tasks with optional filters. Supports filtering by task_list_id, "
            "status, and owner. Returns paginated results."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task_list_id": {
                        "type": "string",
                        "description": "Filter by task list ID",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed", "blocked", "failed"],
                        "description": "Filter by task status",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Filter by task owner",
                    },
                    "skip": {
                        "type": "integer",
                        "description": "Number of tasks to skip (for pagination)",
                        "default": 0,
                        "minimum": 0,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to return",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": [],
            },
        }

    async def execute(self, **kwargs) -> dict[str, Any]:
        """List tasks.

        Args:
            **kwargs: Filter and pagination parameters

        Returns:
            Dictionary with task list or error
        """
        try:
            service = get_task_management_service()

            task_list_response = await service.list_tasks(
                task_list_id=kwargs.get("task_list_id"),
                status=kwargs.get("status"),
                owner=kwargs.get("owner"),
                offset=kwargs.get("skip", 0),
                limit=kwargs.get("limit", 50),
            )

            _logger.info(
                "tasks_listed",
                total=task_list_response.total,
                returned=len(task_list_response.tasks),
            )

            return {
                "success": True,
                "tasks": [task.model_dump() for task in task_list_response.tasks],
                "total": task_list_response.total,
            }

        except Exception as e:
            _logger.error("task_list_failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": f"Failed to list tasks: {e}",
                "error_type": "unknown",
            }
