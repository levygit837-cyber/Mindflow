"""Tasks API endpoints backed by orchestrator planning state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.schemas.api.task_requests import TaskCancelRequest, TaskRetryRequest
from mindflow_backend.schemas.api.task_responses import (
    TaskCancelResponse,
    TaskExecutionsResponse,
    TaskInfoResponse,
    TaskListResponse,
    TaskRetryResponse,
    TaskSubtasksResponse,
)
from mindflow_backend.schemas.tools.planning import TodoItemStatus
from mindflow_backend.services import (
    get_execution_task_service,
    get_todo_planning_service,
)

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=protected_route_dependencies)


class TaskController:
    """Controller that exposes task planning and runtime execution state."""

    def __init__(self) -> None:
        self._todo_service = get_todo_planning_service()
        self._execution_service = get_execution_task_service()

    def _serialize_execution(self, execution: Any) -> dict[str, Any]:
        return {
            "execution_task_id": execution.execution_task_id,
            "task_id": execution.task_id,
            "item_id": execution.item_id,
            "execution_key": execution.execution_key,
            "type": execution.type,
            "status": execution.status,
            "description": execution.description,
            "attempt": execution.attempt,
            "output": execution.output,
            "output_ref": execution.output_ref,
            "error": execution.error,
            "metadata": execution.metadata,
            "created_at": execution.created_at.isoformat(),
            "updated_at": execution.updated_at.isoformat(),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "ended_at": execution.ended_at.isoformat() if execution.ended_at else None,
        }

    def _planning_status(self, summary: Any) -> str:
        return "completed" if summary.closed_at else "in_progress"

    async def get_task_from_decomposition(self, task_id: str) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        summary = snapshot.summary
        todo_list = snapshot.todo_list
        execution_overview = await self._execution_service.get_task_overview(task_id)
        current_focus = await self._todo_service.focus_complex_items(
            session_id=todo_list.session_id,
            task_id=todo_list.task_id,
            limit=1,
        )
        current_step = current_focus.items[0].title if current_focus.items else "Completed"
        planning_status = self._planning_status(summary)
        return {
            "task_id": summary.task_id,
            "status": planning_status,
            "planning_status": planning_status,
            "execution_status": execution_overview["status"],
            "created_at": todo_list.created_at.isoformat(),
            "updated_at": todo_list.updated_at.isoformat(),
            "completed_at": todo_list.closed_at.isoformat() if todo_list.closed_at else None,
            "task_description": todo_list.goal,
            "complexity_level": summary.highest_open_complexity,
            "session_id": todo_list.session_id,
            "source": todo_list.source,
            "progress_percentage": summary.progress_percentage,
            "total_items": summary.total_items,
            "completed_items": summary.completed_items,
            "open_items": summary.open_items,
            "blocked_items": summary.blocked_items,
            "failed_items": summary.failed_items,
            "pending_complexity": summary.pending_complexity,
            "current_step": current_step,
            "is_stale": summary.is_stale,
            "cancel_requested": execution_overview["cancel_requested"],
            "execution_counts": execution_overview["counts"],
            "active_execution_ids": execution_overview["active_execution_ids"],
            "latest_execution_id": execution_overview["latest_execution_id"],
        }

    async def cancel_task_execution(
        self,
        task_id: str,
        *,
        reason: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        todo_list = snapshot.todo_list
        cancel_result = await self._execution_service.request_task_cancellation(
            session_id=todo_list.session_id,
            task_id=task_id,
            reason=reason,
            force=force,
        )
        for item in todo_list.items:
            if item.status not in {TodoItemStatus.PENDING, TodoItemStatus.IN_PROGRESS}:
                continue
            await self._todo_service.update_item_status(
                session_id=todo_list.session_id,
                task_id=task_id,
                item_id=item.item_id,
                status="blocked",
                notes=reason or "Cancellation requested",
            )
        return cancel_result

    async def retry_task_execution(
        self,
        task_id: str,
        *,
        retry_subtasks: bool = False,
        retry_from_beginning: bool = False,
    ) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        todo_list = snapshot.todo_list
        reopened_items = await self._todo_service.preview_retry_items(
            session_id=todo_list.session_id,
            task_id=task_id,
            retry_subtasks=retry_subtasks,
            retry_from_beginning=retry_from_beginning,
        )
        await self._execution_service.clear_task_cancellation(
            session_id=todo_list.session_id,
            task_id=task_id,
        )
        await self._todo_service.retry_items(
            session_id=todo_list.session_id,
            task_id=task_id,
            retry_subtasks=retry_subtasks,
            retry_from_beginning=retry_from_beginning,
        )
        return {
            "task_id": task_id,
            "retry_subtasks": retry_subtasks,
            "retry_from_beginning": retry_from_beginning,
            "reopened_items": reopened_items,
        }

    async def get_session_tasks(self, session_id: str) -> list[dict[str, Any]]:
        summaries = await self._todo_service.get_session_lists(session_id)
        return [
            {
                "task_id": summary.task_id,
                "status": "completed" if summary.closed_at else "in_progress",
                "created_at": summary.updated_at.isoformat(),
                "completed_at": summary.closed_at.isoformat() if summary.closed_at else None,
                "task_description": summary.goal,
                "complexity_level": summary.highest_open_complexity,
                "progress_percentage": summary.progress_percentage,
                "open_items": summary.open_items,
                "completed_items": summary.completed_items,
                "pending_complexity": summary.pending_complexity,
                "source": summary.source,
                "is_stale": summary.is_stale,
            }
            for summary in summaries
        ]

    async def get_task_subtasks(self, task_id: str) -> list[dict[str, Any]]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        subtasks = []
        for item in snapshot.todo_list.items:
            subtasks.append(
                {
                    "subtask_id": item.item_id,
                    "parent_task_id": task_id,
                    "title": item.title,
                    "description": item.description,
                    "status": item.status,
                    "agent_type": item.owner_agent,
                    "priority": item.priority,
                    "dependencies": item.dependencies,
                    "complexity_score": item.complexity_score,
                    "complexity_reason": item.complexity_reason,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "notes": item.notes,
                }
            )
        return subtasks

    async def get_task_executions(self, task_id: str) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        executions = await self._execution_service.list_task_executions(
            session_id=snapshot.todo_list.session_id,
            task_id=task_id,
        )
        summary = await self._execution_service.get_task_overview(task_id)
        return {
            "task_id": task_id,
            "executions": [self._serialize_execution(execution) for execution in executions],
            "summary": summary,
            "total": len(executions),
        }

    async def get_task_progress(self, task_id: str) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        summary = snapshot.summary
        execution_overview = await self._execution_service.get_task_overview(task_id)
        focused = await self._todo_service.focus_complex_items(
            session_id=snapshot.todo_list.session_id,
            task_id=task_id,
            limit=1,
        )
        next_item = focused.items[0] if focused.items else None
        return {
            "task_id": task_id,
            "status": self._planning_status(summary),
            "planning_status": self._planning_status(summary),
            "execution_status": execution_overview["status"],
            "progress_percentage": summary.progress_percentage,
            "current_step": next_item.title if next_item else "Completed",
            "estimated_completion": None,
            "subtasks_completed": summary.completed_items,
            "subtasks_total": summary.total_items,
            "pending_complexity": summary.pending_complexity,
            "highest_open_complexity": summary.highest_open_complexity,
            "errors": [
                item.title
                for item in snapshot.todo_list.items
                if str(item.status) == "failed"
            ],
            "warnings": [
                item.title
                for item in snapshot.todo_list.items
                if str(item.status) == "blocked"
            ],
            "cancel_requested": execution_overview["cancel_requested"],
            "active_execution_ids": execution_overview["active_execution_ids"],
        }


task_controller = TaskController()


@router.get("/{task_id}", response_model=TaskInfoResponse)
async def get_task_status(task_id: str):
    """Get status and information for a specific task."""
    try:
        task_info = await task_controller.get_task_from_decomposition(task_id)
        return TaskInfoResponse(
            success=True,
            message="Task information retrieved successfully",
            task=task_info,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(task_id: str, request: TaskCancelRequest | None = None):
    """Cancel active runtime executions and block open planning items."""
    try:
        cancel_result = await task_controller.cancel_task_execution(
            task_id,
            reason=request.reason if request else None,
            force=request.force if request else False,
        )
        return TaskCancelResponse(
            success=True,
            message="Task cancelled successfully",
            task_id=task_id,
            cancel_result=cancel_result,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/{task_id}/retry", response_model=TaskRetryResponse)
async def retry_task(task_id: str, request: TaskRetryRequest):
    """Reopen failed/blocked planning items and clear cancellation state."""
    try:
        retry_result = await task_controller.retry_task_execution(
            task_id,
            retry_subtasks=request.retry_subtasks,
            retry_from_beginning=request.retry_from_beginning,
        )
        return TaskRetryResponse(
            success=True,
            message="Task retry initiated successfully",
            task_id=task_id,
            retry_result=retry_result,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/session/{session_id}", response_model=TaskListResponse)
async def get_session_tasks(session_id: str):
    """Get all tasks associated with a specific session."""
    try:
        tasks = await task_controller.get_session_tasks(session_id)
        return TaskListResponse(
            success=True,
            message="Session tasks retrieved successfully",
            session_id=session_id,
            tasks=tasks,
            total=len(tasks),
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{task_id}/subtasks", response_model=TaskSubtasksResponse)
async def get_task_subtasks(task_id: str):
    """Get subtasks projected from the current todo list."""
    try:
        subtasks = await task_controller.get_task_subtasks(task_id)
        return TaskSubtasksResponse(
            success=True,
            message="Task subtasks retrieved successfully",
            task_id=task_id,
            subtasks=subtasks,
            total=len(subtasks),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{task_id}/executions", response_model=TaskExecutionsResponse)
async def get_task_executions(task_id: str):
    """Get runtime execution tasks associated with a planning task."""
    try:
        execution_info = await task_controller.get_task_executions(task_id)
        return TaskExecutionsResponse(
            success=True,
            message="Task executions retrieved successfully",
            task_id=task_id,
            executions=execution_info["executions"],
            summary=execution_info["summary"],
            total=execution_info["total"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{task_id}/progress")
async def get_task_progress(task_id: str):
    """Get real-time progress information for a task."""
    try:
        progress_info = await task_controller.get_task_progress(task_id)
        return {
            "success": True,
            "message": "Task progress retrieved successfully",
            "progress": progress_info,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
