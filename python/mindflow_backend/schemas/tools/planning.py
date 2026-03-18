"""Planning tool contracts and schemas for session-scoped todo lists."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from mindflow_backend.schemas.tools.tool_config import ToolParameter, ToolSchema


class TodoItemStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class TodoItemContract(BaseModel):
    item_id: str
    title: str
    description: str = ""
    owner_agent: str | None = None
    priority: str = "medium"
    dependencies: list[str] = Field(default_factory=list)
    complexity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity_reason: str = ""
    status: TodoItemStatus = TodoItemStatus.PENDING
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class TodoListContract(BaseModel):
    session_id: str
    task_id: str
    goal: str
    source: str = "runtime"
    items: list[TodoItemContract] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None


class TodoListSummary(BaseModel):
    session_id: str
    task_id: str
    goal: str
    source: str
    total_items: int = 0
    completed_items: int = 0
    open_items: int = 0
    blocked_items: int = 0
    failed_items: int = 0
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    pending_complexity: float = Field(default=0.0, ge=0.0)
    highest_open_complexity: float = Field(default=0.0, ge=0.0, le=1.0)
    is_stale: bool = False
    updated_at: datetime
    closed_at: datetime | None = None


class TodoListWriteRequest(BaseModel):
    task_id: str
    goal: str
    items: list[TodoItemContract] = Field(default_factory=list)
    source: str = "planner"


class TodoListReadResponse(BaseModel):
    todo_list: TodoListContract
    summary: TodoListSummary


class TodoListFocusResponse(BaseModel):
    task_id: str
    goal: str
    items: list[TodoItemContract] = Field(default_factory=list)
    summary: TodoListSummary


WRITE_TODOS_SCHEMA = ToolSchema(
    name="write_todos",
    description="Replace the session-scoped todo list for a planned execution task",
    category="planning",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="task_id", type="string", description="Planned execution task identifier", required=True),
        ToolParameter(name="goal", type="string", description="High-level goal for the todo list", required=True),
        ToolParameter(name="items", type="array", description="Full todo item list to persist", required=True),
        ToolParameter(name="source", type="string", description="Planner/runtime source for the list", required=False),
    ],
    returns={"type": "object", "description": "Todo list snapshot and summary"},
)


READ_TODOS_SCHEMA = ToolSchema(
    name="read_todos",
    description="Read the latest todo list snapshot for a planned execution task",
    category="planning",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="task_id", type="string", description="Planned execution task identifier", required=True),
    ],
    returns={"type": "object", "description": "Todo list snapshot and summary"},
)


FOCUS_TODOS_SCHEMA = ToolSchema(
    name="focus_todos",
    description="Return the most complex open todo items for the current planned execution task",
    category="planning",
    parameters=[
        ToolParameter(name="session_id", type="string", description="Chat session identifier", required=False),
        ToolParameter(name="task_id", type="string", description="Planned execution task identifier", required=True),
        ToolParameter(name="limit", type="integer", description="Maximum number of items to return", required=False),
    ],
    returns={"type": "object", "description": "Focused open todo items and summary"},
)
