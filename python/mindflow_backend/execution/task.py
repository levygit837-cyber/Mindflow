"""Task management system for MindFlow execution.

Adapted from Claude Code's Task.ts to provide task lifecycle management
for different execution types (bash, agent, remote, teammate, workflow).
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class TaskType(str, Enum):
    """Types of tasks that can be executed."""
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKFLOW = "local_workflow"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


class TaskStatus(str, Enum):
    """Status of a task during its lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


def is_terminal_task_status(status: TaskStatus) -> bool:
    """Check if a task is in a terminal state.

    Terminal tasks will not transition further. Used to guard against
    injecting messages into dead teammates, evicting finished tasks from
    AppState, and orphan-cleanup paths.

    Args:
        status: The task status to check

    Returns:
        True if the task is in a terminal state
    """
    return status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)


@dataclass
class TaskHandle:
    """Handle for a running task with cleanup capability."""
    task_id: str
    cleanup: Any | None = None  # Callable or None


@dataclass
class TaskContext:
    """Context provided to tasks during execution."""
    abort_controller: Any
    get_app_state: Any
    set_app_state: Any


# Base fields shared by all task states
@dataclass
class TaskStateBase:
    """Base state for all task types."""
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    tool_use_id: str | None = None
    start_time: int = 0
    end_time: int | None = None
    total_paused_ms: int = 0
    output_file: Path | None = None
    output_offset: int = 0
    notified: bool = False


@dataclass
class LocalShellSpawnInput:
    """Input for spawning a local shell task."""
    command: str
    description: str
    timeout: int | None = None
    tool_use_id: str | None = None
    agent_id: str | None = None
    kind: str = "bash"  # "bash" or "monitor"


# Task ID prefixes
TASK_ID_PREFIXES: dict[TaskType, str] = {
    TaskType.LOCAL_BASH: "b",  # Keep as 'b' for backward compatibility
    TaskType.LOCAL_AGENT: "a",
    TaskType.REMOTE_AGENT: "r",
    TaskType.IN_PROCESS_TEAMMATE: "t",
    TaskType.LOCAL_WORKFLOW: "w",
    TaskType.MONITOR_MCP: "m",
    TaskType.DREAM: "d",
}


def get_task_id_prefix(task_type: TaskType) -> str:
    """Get the prefix for a given task type."""
    return TASK_ID_PREFIXES.get(task_type, "x")


# Case-insensitive-safe alphabet (digits + lowercase) for task IDs
# 36^8 ≈ 2.8 trillion combinations, sufficient to resist brute-force symlink attacks
TASK_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def generate_task_id(task_type: TaskType) -> str:
    """Generate a unique task ID for the given task type.

    Args:
        task_type: The type of task

    Returns:
        A unique task ID with prefix and random characters
    """
    prefix = get_task_id_prefix(task_type)
    random_bytes = random.randbytes(8)
    task_id = prefix
    for byte in random_bytes:
        task_id += TASK_ID_ALPHABET[byte % len(TASK_ID_ALPHABET)]
    return task_id


def create_task_state_base(
    task_id: str,
    task_type: TaskType,
    description: str,
    tool_use_id: str | None = None,
) -> TaskStateBase:
    """Create a base task state.

    Args:
        task_id: The task ID
        task_type: The task type
        description: Task description
        tool_use_id: Optional tool use ID

    Returns:
        A TaskStateBase instance
    """
    return TaskStateBase(
        id=task_id,
        type=task_type,
        status=TaskStatus.PENDING,
        description=description,
        tool_use_id=tool_use_id,
        start_time=0,
        output_file=None,
        output_offset=0,
        notified=False,
    )


def get_task_output_path(task_id: str) -> Path:
    """Get the output file path for a task.

    Args:
        task_id: The task ID

    Returns:
        Path to the task's output file
    """
    # This would typically use a configured output directory
    # For now, using a temporary directory pattern
    from mindflow_backend.infra.config import get_settings

    settings = get_settings()
    base_dir = Path(settings.workspace_root) if hasattr(settings, "workspace_root") else Path("/tmp")
    task_dir = base_dir / ".mindflow" / "task_outputs"
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir / f"{task_id}.txt"
