"""Adapter to bridge TodoPlanningService and TaskManagementService.

This adapter provides backward compatibility by mapping TodoItemContract
to TaskManagementService's Task model, allowing gradual migration.
"""

from __future__ import annotations

from datetime import datetime

from mindflow_backend.schemas.tasks import TaskCreate, TaskResponse, TaskUpdate
from mindflow_backend.schemas.tools.planning import TodoItemContract, TodoItemStatus


class TodoToTaskAdapter:
    """Adapter to convert between TodoItemContract and Task models."""

    # Map TodoItemStatus to Task status
    STATUS_MAP = {
        TodoItemStatus.PENDING: "pending",
        TodoItemStatus.IN_PROGRESS: "in_progress",
        TodoItemStatus.COMPLETED: "completed",
        TodoItemStatus.BLOCKED: "blocked",
        TodoItemStatus.FAILED: "failed",
    }

    # Reverse map
    TASK_STATUS_TO_TODO = {v: k for k, v in STATUS_MAP.items()}

    @staticmethod
    def todo_item_to_task_create(
        item: TodoItemContract,
        task_list_id: str,
    ) -> TaskCreate:
        """Convert TodoItemContract to TaskCreate.

        Args:
            item: Todo item to convert
            task_list_id: Task list ID (session_id + task_id)

        Returns:
            TaskCreate schema
        """
        # Store todo-specific metadata in task_metadata
        metadata = {
            "complexity_score": item.complexity_score,
            "complexity_reason": item.complexity_reason,
            "priority": item.priority,
            "notes": item.notes,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }

        return TaskCreate(
            task_list_id=task_list_id,
            subject=item.title,
            description=item.description or "",
            active_form=item.title,  # Use title as active form
            owner=item.owner_agent,
            status=TodoToTaskAdapter.STATUS_MAP.get(item.status, "pending"),
            task_metadata=metadata,
            blocks=[],  # Dependencies handled separately
            blocked_by=[],
        )

    @staticmethod
    def todo_item_to_task_update(
        item: TodoItemContract,
    ) -> TaskUpdate:
        """Convert TodoItemContract to TaskUpdate.

        Args:
            item: Todo item to convert

        Returns:
            TaskUpdate schema
        """
        metadata = {
            "complexity_score": item.complexity_score,
            "complexity_reason": item.complexity_reason,
            "priority": item.priority,
            "notes": item.notes,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
        }

        return TaskUpdate(
            subject=item.title,
            description=item.description,
            owner=item.owner_agent,
            status=TodoToTaskAdapter.STATUS_MAP.get(item.status, "pending"),
            task_metadata=metadata,
        )

    @staticmethod
    def task_to_todo_item(
        task: TaskResponse,
        item_id: str | None = None,
        dependencies: list[str] | None = None,
    ) -> TodoItemContract:
        """Convert TaskResponse to TodoItemContract.

        Args:
            task: Task response to convert
            item_id: Optional item ID (defaults to str(task.id))
            dependencies: Optional list of dependency item IDs

        Returns:
            TodoItemContract
        """
        metadata = task.task_metadata or {}

        # Parse datetime strings from metadata
        created_at = None
        if metadata.get("created_at"):
            try:
                created_at = datetime.fromisoformat(metadata["created_at"])
            except (ValueError, TypeError):
                created_at = task.created_at

        completed_at = None
        if metadata.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(metadata["completed_at"])
            except (ValueError, TypeError):
                completed_at = None

        # Map task status back to TodoItemStatus
        todo_status = TodoToTaskAdapter.TASK_STATUS_TO_TODO.get(
            task.status,
            TodoItemStatus.PENDING,
        )

        return TodoItemContract(
            item_id=item_id or str(task.id),
            title=task.subject,
            description=task.description or "",
            owner_agent=task.owner or "analyst",
            priority=metadata.get("priority", "medium"),
            dependencies=dependencies or [],
            complexity_score=metadata.get("complexity_score", 0.35),
            complexity_reason=metadata.get("complexity_reason", ""),
            status=todo_status,
            notes=metadata.get("notes"),
            created_at=created_at or task.created_at,
            updated_at=task.updated_at,
            completed_at=completed_at,
        )

    @staticmethod
    def make_task_list_id(session_id: str, task_id: str) -> str:
        """Create a task_list_id from session_id and task_id.

        Args:
            session_id: Session ID
            task_id: Task ID

        Returns:
            Combined task_list_id
        """
        return f"{session_id}:{task_id}"

    @staticmethod
    def parse_task_list_id(task_list_id: str) -> tuple[str, str]:
        """Parse task_list_id into session_id and task_id.

        Args:
            task_list_id: Combined task_list_id

        Returns:
            Tuple of (session_id, task_id)

        Raises:
            ValueError: If task_list_id format is invalid
        """
        parts = task_list_id.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid task_list_id format: {task_list_id}")
        return parts[0], parts[1]
