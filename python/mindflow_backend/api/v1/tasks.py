"""Tasks API endpoints backed by orchestrator planning state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from mindflow_backend.api.dependencies import protected_route_dependencies
from mindflow_backend.schemas.api.task_requests import TaskCancelRequest, TaskRetryRequest
from mindflow_backend.schemas.api.task_responses import (
    TaskCancelResponse,
    TaskInfoResponse,
    TaskListResponse,
    TaskRetryResponse,
    TaskSubtasksResponse,
)
from mindflow_backend.services import get_todo_planning_service

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=protected_route_dependencies)


class TaskController:
    """Controller that exposes read-only task planning state."""

    def __init__(self) -> None:
        self._todo_service = get_todo_planning_service()

    async def get_task_from_decomposition(self, task_id: str) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        summary = snapshot.summary
        todo_list = snapshot.todo_list
        current_focus = await self._todo_service.focus_complex_items(
            session_id=todo_list.session_id,
            task_id=todo_list.task_id,
            limit=1,
        )
        current_step = current_focus.items[0].title if current_focus.items else "Completed"
        return {
            "task_id": summary.task_id,
            "status": "completed" if summary.closed_at else "in_progress",
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
        }

    async def cancel_task_execution(self, task_id: str) -> dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task cancellation is not exposed via HTTP in this version",
        )

    async def retry_task_execution(self, task_id: str, retry_subtasks: bool = False) -> dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task retry is not exposed via HTTP in this version",
        )

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

    async def get_task_progress(self, task_id: str) -> dict[str, Any]:
        snapshot = await self._todo_service.get_list_by_task_id(task_id)
        summary = snapshot.summary
        focused = await self._todo_service.focus_complex_items(
            session_id=snapshot.todo_list.session_id,
            task_id=task_id,
            limit=1,
        )
        next_item = focused.items[0] if focused.items else None
        return {
            "task_id": task_id,
            "status": "completed" if summary.closed_at else "in_progress",
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
    """Cancellation is intentionally not exposed in this read-only API."""
    try:
        cancel_result = await task_controller.cancel_task_execution(task_id)
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
    """Retry is intentionally not exposed in this read-only API."""
    try:
        retry_result = await task_controller.retry_task_execution(task_id, request.retry_subtasks)
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
