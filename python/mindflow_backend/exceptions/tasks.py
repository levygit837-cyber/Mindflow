"""Task management exceptions."""

from __future__ import annotations


class TaskError(Exception):
    """Base exception for task management errors."""
    pass


class TaskNotFoundError(TaskError):
    """Raised when a task is not found."""

    def __init__(self, task_id: int | str):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class TaskVersionConflictError(TaskError):
    """Raised when optimistic locking detects a version conflict."""

    def __init__(self, task_id: int, expected_version: int, actual_version: int):
        self.task_id = task_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"Task {task_id} version conflict: expected {expected_version}, "
            f"but current version is {actual_version}"
        )


class CircularDependencyError(TaskError):
    """Raised when a circular dependency is detected in the task graph."""

    def __init__(self, cycle: list[int]):
        self.cycle = cycle
        cycle_str = " -> ".join(str(task_id) for task_id in cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class InvalidStatusTransitionError(TaskError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, task_id: int, from_status: str, to_status: str):
        self.task_id = task_id
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Invalid status transition for task {task_id}: "
            f"{from_status} -> {to_status}"
        )


class TaskDependencyError(TaskError):
    """Raised when a task dependency operation fails."""

    def __init__(self, message: str):
        super().__init__(message)
