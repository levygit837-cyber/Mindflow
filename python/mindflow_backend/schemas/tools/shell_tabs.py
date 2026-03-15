"""Shell tab contracts and tool schemas.

Session-scoped shell tabs behave like mutable process records. The actual shell
execution remains in-memory and ephemeral; the contracts below are the canonical
shapes exposed to tools, services, and API responses.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


class ShellTabState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class ShellTabContract(BaseModel):
    tab_id: str
    session_id: str
    cwd: str
    title: str
    pid: int | None = None
    state: ShellTabState = ShellTabState.IDLE
    last_command: str | None = None
    last_exit_code: int | None = None
    stdout_buffer: str = ""
    stderr_buffer: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    closed_at: datetime | None = None


class ShellTabSnapshot(BaseModel):
    tab_id: str
    session_id: str
    state: ShellTabState
    stdout_buffer: str = ""
    stderr_buffer: str = ""
    updated_at: datetime


class ShellTabStatusResponse(BaseModel):
    tab_id: str
    session_id: str
    cwd: str
    title: str
    pid: int | None = None
    state: ShellTabState
    last_command: str | None = None
    last_exit_code: int | None = None
    stdout_preview: str = ""
    stderr_preview: str = ""
    updated_at: datetime


class ShellTabCreateRequest(BaseModel):
    cwd: str | None = None
    title: str | None = None


class ShellTabExecRequest(BaseModel):
    command: str


SHELL_TAB_OPEN_SCHEMA = ToolSchema(
    name="shell_tab_open",
    description="Create a session-scoped shell tab that preserves cwd and command history",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="cwd", type="string", description="Working directory for the tab", required=False),
        ToolParameter(name="title", type="string", description="Optional tab title", required=False),
    ],
    returns={
        "type": "object",
        "description": "Shell tab contract",
    },
)


SHELL_TAB_LIST_SCHEMA = ToolSchema(
    name="shell_tab_list",
    description="List shell tabs for the current chat session",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
    ],
    returns={"type": "array", "description": "List of shell tab contracts"},
)


SHELL_TAB_STATUS_SCHEMA = ToolSchema(
    name="shell_tab_status",
    description="Get the latest status for a shell tab",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="tab_id", type="string", description="Shell tab identifier", required=True),
    ],
    returns={"type": "object", "description": "Shell tab status response"},
)


SHELL_TAB_EXEC_SCHEMA = ToolSchema(
    name="shell_tab_exec",
    description="Execute a command inside an existing shell tab and update its buffers",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="tab_id", type="string", description="Shell tab identifier", required=True),
        ToolParameter(name="command", type="string", description="Command to execute", required=True),
    ],
    returns={"type": "object", "description": "Updated shell tab contract after execution"},
)


SHELL_TAB_READ_SCHEMA = ToolSchema(
    name="shell_tab_read",
    description="Read the accumulated stdout/stderr buffers for a shell tab",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="tab_id", type="string", description="Shell tab identifier", required=True),
    ],
    returns={"type": "object", "description": "Shell tab buffer snapshot"},
)


SHELL_TAB_CLOSE_SCHEMA = ToolSchema(
    name="shell_tab_close",
    description="Terminate a shell tab and any active process attached to it",
    category="system",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="tab_id", type="string", description="Shell tab identifier", required=True),
    ],
    returns={"type": "object", "description": "Shell tab contract after closure"},
)
