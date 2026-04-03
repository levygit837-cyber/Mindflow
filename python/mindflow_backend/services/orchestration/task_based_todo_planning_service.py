"""Task-based TodoPlanningService implementation using TaskManagementService backend.

This service provides backward compatibility with the original TodoPlanningService
interface while using persistent PostgreSQL storage via TaskManagementService.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.tasks import TaskCreate, TaskUpdate
from mindflow_backend.schemas.tools.planning import (
    TodoItemContract,
    TodoItemStatus,
    TodoListContract,
    TodoListFocusResponse,
    TodoListReadResponse,
    TodoListSummary,
)
from mindflow_backend.services.orchestration.todo_task_adapter import TodoToTaskAdapter

if TYPE_CHECKING:
    from mindflow_backend.schemas.orchestration.decomposition.decomposition_v2 import (
        SubTaskContract,
    )
    from mindflow_backend.services.orchestration.task_management_service import (
        TaskManagementService,
    )

_logger = get_logger(__name__)

_OPEN_STATUSES = {
    TodoItemStatus.PENDING,
    TodoItemStatus.IN_PROGRESS,
    TodoItemStatus.BLOCKED,
    TodoItemStatus.FAILED,
}
_PRIORITY_WEIGHT = {"low": 1, "medium": 2, "high": 3}


class TaskBasedTodoPlanningService:
    """TodoPlanningService implementation using TaskManagementService backend.

    This service maintains backward compatibility with the original TodoPlanningService
    interface while using persistent PostgreSQL storage.
    """

    def __init__(
        self,
        *,
        stale_after: timedelta = timedelta(minutes=15),
        task_service: TaskManagementService | None = None,
    ) -> None:
        self._task_service = task_service  # Will be lazily initialized
        self._stale_after = stale_after
        self._lock = asyncio.Lock()
        self._adapter = TodoToTaskAdapter()

    def _get_task_service(self) -> TaskManagementService:
        """Get task service, lazily initializing if needed."""
        if self._task_service is None:
            # Use factory function to avoid circular import
            from mindflow_backend.services.orchestration import get_task_management_service
            self._task_service = get_task_management_service()
        return self._task_service

    async def replace_list(
        self,
        session_id: str,
        task_id: str,
        goal: str,
        items: list[dict[str, Any] | TodoItemContract],
        source: str,
    ) -> TodoListReadResponse:
        """Replace entire todo list with new items.

        Args:
            session_id: Session ID
            task_id: Task ID
            goal: Goal description
            items: List of todo items
            source: Source of the list (e.g., "planner", "decomposition")

        Returns:
            TodoListReadResponse with updated list
        """
        task_list_id = self._adapter.make_task_list_id(session_id, task_id)

        async with self._lock:
            # Delete existing tasks for this list
            existing_response = await self._get_task_service().list_tasks(
                task_list_id=task_list_id,
                limit=1000,
            )

            for existing_task in existing_response.tasks:
                await self._get_task_service().delete_task(existing_task.id)

            # Create new tasks
            item_id_to_task_id: dict[str, int] = {}
            normalized_items: list[TodoItemContract] = []

            # First pass: create all tasks without dependencies
            for raw_item in items:
                if isinstance(raw_item, TodoItemContract):
                    item = raw_item
                else:
                    item = TodoItemContract.model_validate(raw_item)

                normalized_items.append(item)

                task_create = self._adapter.todo_item_to_task_create(item, task_list_id)
                # Store goal and source in metadata
                task_create.task_metadata["goal"] = goal
                task_create.task_metadata["source"] = source
                task_create.task_metadata["item_id"] = item.item_id

                task_response = await self._get_task_service().create_task(
                    task_create,
                    session_id=session_id,
                )
                item_id_to_task_id[item.item_id] = task_response.id

            # Second pass: add dependencies
            for item in normalized_items:
                if not item.dependencies:
                    continue

                task_id_int = item_id_to_task_id.get(item.item_id)
                if task_id_int is None:
                    continue

                # Map item_id dependencies to task_id dependencies
                blocked_by_task_ids = [
                    item_id_to_task_id[dep_item_id]
                    for dep_item_id in item.dependencies
                    if dep_item_id in item_id_to_task_id
                ]

                if blocked_by_task_ids:
                    update = TaskUpdate(add_blocked_by=blocked_by_task_ids)
                    await self._get_task_service().update_task(
                        task_id_int,
                        update,
                        session_id=session_id,
                    )

        _logger.info(
            "todo_list_replaced",
            session_id=session_id,
            task_id=task_id,
            items=len(normalized_items),
            source=source,
        )

        return await self.get_list(session_id, task_id)

    async def get_list(self, session_id: str, task_id: str) -> TodoListReadResponse:
        """Get todo list for session and task.

        Args:
            session_id: Session ID
            task_id: Task ID

        Returns:
            TodoListReadResponse with list and summary
        """
        task_list_id = self._adapter.make_task_list_id(session_id, task_id)

        # Get all tasks for this list
        response = await self._get_task_service().list_tasks(
            task_list_id=task_list_id,
            limit=1000,
        )

        if not response.tasks:
            raise ValueError(f"Todo list not found for session={session_id} task={task_id}")

        # Build item_id to task_id mapping
        task_id_to_item_id: dict[int, str] = {}
        for task in response.tasks:
            item_id = task.task_metadata.get("item_id", str(task.id))
            task_id_to_item_id[task.id] = item_id

        # Convert tasks to todo items
        items: list[TodoItemContract] = []
        goal = ""
        source = ""
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        for task in response.tasks:
            item_id = task.task_metadata.get("item_id", str(task.id))

            # Map blocked_by task IDs to item IDs
            dependencies = [
                task_id_to_item_id[dep_task_id]
                for dep_task_id in task.blocked_by
                if dep_task_id in task_id_to_item_id
            ]

            todo_item = self._adapter.task_to_todo_item(
                task,
                item_id=item_id,
                dependencies=dependencies,
            )
            items.append(todo_item)

            # Extract metadata from first task
            if not goal:
                goal = task.task_metadata.get("goal", "")
            if not source:
                source = task.task_metadata.get("source", "")
            if task.created_at < created_at:
                created_at = task.created_at
            if task.updated_at > updated_at:
                updated_at = task.updated_at

        # Check if list is closed (all items completed)
        closed_at = None
        if items and all(item.status == TodoItemStatus.COMPLETED for item in items):
            closed_at = updated_at

        todo_list = TodoListContract(
            session_id=session_id,
            task_id=task_id,
            goal=goal,
            source=source,
            items=items,
            created_at=created_at,
            updated_at=updated_at,
            closed_at=closed_at,
        )

        return TodoListReadResponse(
            todo_list=todo_list,
            summary=self._build_summary(todo_list),
        )

    async def get_session_lists(self, session_id: str) -> list[TodoListSummary]:
        """Get all todo lists for a session.

        Args:
            session_id: Session ID

        Returns:
            List of TodoListSummary
        """
        # Get all tasks for this session (all task_list_ids starting with session_id)
        # This is a limitation - we need to query by prefix
        # For now, we'll return empty list and log a warning
        _logger.warning(
            "get_session_lists_not_fully_supported",
            session_id=session_id,
            reason="TaskManagementService doesn't support prefix queries on task_list_id",
        )
        return []

    async def get_list_by_task_id(self, task_id: str) -> TodoListReadResponse:
        """Get todo list by task ID only.

        Args:
            task_id: Task ID

        Returns:
            TodoListReadResponse

        Raises:
            ValueError: If list not found
        """
        # This is challenging without session_id
        # We'd need to query all tasks and find matching task_list_id
        raise NotImplementedError(
            "get_list_by_task_id requires session_id. "
            "Use get_list(session_id, task_id) instead."
        )

    async def update_item_status(
        self,
        session_id: str,
        task_id: str,
        item_id: str,
        status: str,
        notes: str | None = None,
    ) -> TodoListReadResponse:
        """Update status of a todo item.

        Args:
            session_id: Session ID
            task_id: Task ID
            item_id: Item ID
            status: New status
            notes: Optional notes

        Returns:
            TodoListReadResponse with updated list
        """
        task_list_id = self._adapter.make_task_list_id(session_id, task_id)

        # Find the task with matching item_id
        response = await self._get_task_service().list_tasks(
            task_list_id=task_list_id,
            limit=1000,
        )

        target_task = None
        for task in response.tasks:
            if task.task_metadata.get("item_id") == item_id:
                target_task = task
                break

        if target_task is None:
            raise ValueError(f"Todo item not found: {item_id}")

        # Update task status
        normalized_status = TodoItemStatus(status)
        task_status = self._adapter.STATUS_MAP.get(normalized_status, "pending")

        metadata_update = dict(target_task.task_metadata)
        if notes is not None:
            metadata_update["notes"] = notes
        if normalized_status == TodoItemStatus.COMPLETED:
            metadata_update["completed_at"] = datetime.now(UTC).isoformat()

        update = TaskUpdate(
            status=task_status,
            task_metadata=metadata_update,
        )

        await self._get_task_service().update_task(
            target_task.id,
            update,
            session_id=session_id,
        )

        _logger.info(
            "todo_item_status_updated",
            session_id=session_id,
            task_id=task_id,
            item_id=item_id,
            status=status,
        )

        return await self.get_list(session_id, task_id)

    async def focus_complex_items(
        self,
        session_id: str,
        task_id: str,
        limit: int = 3,
    ) -> TodoListFocusResponse:
        """Get most complex open items.

        Args:
            session_id: Session ID
            task_id: Task ID
            limit: Maximum number of items to return

        Returns:
            TodoListFocusResponse with focused items
        """
        list_response = await self.get_list(session_id, task_id)
        todo_list = list_response.todo_list

        open_items = [
            item.model_copy(deep=True)
            for item in todo_list.items
            if item.status in _OPEN_STATUSES
        ]

        open_items.sort(
            key=lambda item: (
                -item.complexity_score,
                -len(item.dependencies),
                -_PRIORITY_WEIGHT.get(item.priority, 2),
                item.title.lower(),
            )
        )

        return TodoListFocusResponse(
            task_id=task_id,
            goal=todo_list.goal,
            items=open_items[: max(limit, 1)],
            summary=list_response.summary,
        )

    async def is_stale(self, session_id: str, task_id: str) -> bool:
        """Check if todo list is stale.

        Args:
            session_id: Session ID
            task_id: Task ID

        Returns:
            True if stale, False otherwise
        """
        try:
            list_response = await self.get_list(session_id, task_id)
            todo_list = list_response.todo_list

            if todo_list.closed_at is not None:
                return False

            if not any(item.status in _OPEN_STATUSES for item in todo_list.items):
                return False

            return (datetime.now(UTC) - todo_list.updated_at) > self._stale_after

        except ValueError:
            return True

    async def close_list(self, session_id: str, task_id: str) -> TodoListReadResponse:
        """Close a todo list.

        Args:
            session_id: Session ID
            task_id: Task ID

        Returns:
            TodoListReadResponse with closed list
        """
        # Mark all tasks as completed
        task_list_id = self._adapter.make_task_list_id(session_id, task_id)

        response = await self._get_task_service().list_tasks(
            task_list_id=task_list_id,
            limit=1000,
        )

        for task in response.tasks:
            if task.status != "completed":
                update = TaskUpdate(status="completed")
                await self._get_task_service().update_task(
                    task.id,
                    update,
                    session_id=session_id,
                )

        return await self.get_list(session_id, task_id)

    async def preview_retry_items(
        self,
        *,
        session_id: str,
        task_id: str,
        retry_subtasks: bool = False,
        retry_from_beginning: bool = False,
    ) -> list[str]:
        """Preview which items would be retried.

        Args:
            session_id: Session ID
            task_id: Task ID
            retry_subtasks: Whether to retry dependent subtasks
            retry_from_beginning: Whether to retry all items

        Returns:
            List of item IDs that would be retried
        """
        list_response = await self.get_list(session_id, task_id)
        todo_list = list_response.todo_list

        return self._select_retry_item_ids(
            todo_list,
            retry_subtasks=retry_subtasks,
            retry_from_beginning=retry_from_beginning,
        )

    async def retry_items(
        self,
        *,
        session_id: str,
        task_id: str,
        retry_subtasks: bool = False,
        retry_from_beginning: bool = False,
    ) -> TodoListReadResponse:
        """Retry failed/blocked items.

        Args:
            session_id: Session ID
            task_id: Task ID
            retry_subtasks: Whether to retry dependent subtasks
            retry_from_beginning: Whether to retry all items

        Returns:
            TodoListReadResponse with updated list
        """
        list_response = await self.get_list(session_id, task_id)
        todo_list = list_response.todo_list

        retry_item_ids = set(
            self._select_retry_item_ids(
                todo_list,
                retry_subtasks=retry_subtasks,
                retry_from_beginning=retry_from_beginning,
            )
        )

        # Update status for retry items
        for item in todo_list.items:
            if item.item_id not in retry_item_ids:
                continue

            await self.update_item_status(
                session_id=session_id,
                task_id=task_id,
                item_id=item.item_id,
                status=TodoItemStatus.PENDING.value,
                notes=None,
            )

        return await self.get_list(session_id, task_id)

    def _select_retry_item_ids(
        self,
        todo_list: TodoListContract,
        *,
        retry_subtasks: bool,
        retry_from_beginning: bool,
    ) -> list[str]:
        """Select item IDs to retry based on criteria."""
        if retry_from_beginning:
            return [item.item_id for item in todo_list.items]

        retry_ids = {
            item.item_id
            for item in todo_list.items
            if item.status
            in {
                TodoItemStatus.IN_PROGRESS,
                TodoItemStatus.BLOCKED,
                TodoItemStatus.FAILED,
            }
        }

        if retry_subtasks and retry_ids:
            expanded = True
            while expanded:
                expanded = False
                for item in todo_list.items:
                    if item.item_id in retry_ids:
                        continue
                    if any(dependency in retry_ids for dependency in item.dependencies):
                        retry_ids.add(item.item_id)
                        expanded = True

        return [item.item_id for item in todo_list.items if item.item_id in retry_ids]

    def _build_summary(self, todo_list: TodoListContract) -> TodoListSummary:
        """Build summary statistics for todo list."""
        completed_items = sum(
            1 for item in todo_list.items if item.status == TodoItemStatus.COMPLETED
        )
        blocked_items = sum(
            1 for item in todo_list.items if item.status == TodoItemStatus.BLOCKED
        )
        failed_items = sum(
            1 for item in todo_list.items if item.status == TodoItemStatus.FAILED
        )
        open_items = sum(1 for item in todo_list.items if item.status in _OPEN_STATUSES)

        total_complexity = sum(max(item.complexity_score, 0.1) for item in todo_list.items)
        completed_complexity = sum(
            max(item.complexity_score, 0.1)
            for item in todo_list.items
            if item.status == TodoItemStatus.COMPLETED
        )
        pending_complexity = sum(
            item.complexity_score
            for item in todo_list.items
            if item.status in _OPEN_STATUSES
        )
        highest_open_complexity = max(
            (
                item.complexity_score
                for item in todo_list.items
                if item.status in _OPEN_STATUSES
            ),
            default=0.0,
        )

        progress = (
            100.0
            if total_complexity == 0
            else round((completed_complexity / total_complexity) * 100.0, 2)
        )

        return TodoListSummary(
            session_id=todo_list.session_id,
            task_id=todo_list.task_id,
            goal=todo_list.goal,
            source=todo_list.source,
            total_items=len(todo_list.items),
            completed_items=completed_items,
            open_items=open_items,
            blocked_items=blocked_items,
            failed_items=failed_items,
            progress_percentage=progress,
            pending_complexity=round(pending_complexity, 3),
            highest_open_complexity=round(highest_open_complexity, 3),
            is_stale=(
                (datetime.now(UTC) - todo_list.updated_at) > self._stale_after
                if todo_list.closed_at is None
                else False
            ),
            updated_at=todo_list.updated_at,
            closed_at=todo_list.closed_at,
        )
