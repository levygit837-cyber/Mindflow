"""Planning layer contracts for the Orchestrator planning workflow.

This module defines the contracts for the planning phase:
- Plan creation and storage
- Plan confirmation workflow
- Plan → TodoList conversion
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PlanStatus(StrEnum):
    """Status of a planning document."""
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    IN_EXECUTION = "in_execution"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanTask(BaseModel):
    """A single task within a plan."""
    task_id: str
    title: str
    description: str = ""
    depends_on: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    action: str = "EDIT"  # ADD, EDIT, REMOVE
    agent: str = "analyst"
    priority: str = "medium"
    verification: str = ""
    status: str = "pending"


class PlanDocument(BaseModel):
    """A structured plan document stored as .md."""
    plan_id: str
    session_id: str
    goal: str
    intent: str = ""
    work_type: str = "new_feature"  # new_feature, refactoring, bug_fix, migration, integration, infrastructure, test_coverage
    scope: str = ""
    file_impact_matrix: list[dict[str, str]] = Field(default_factory=list)
    tasks: list[PlanTask] = Field(default_factory=list)
    test_plan: str = ""
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None
    folder_path: str | None = None
    source_context: str = ""  # Context gathered before planning

    def to_markdown(self) -> str:
        """Convert the plan to markdown format for storage."""
        lines = [
            f"# Plan: {self.goal}",
            "",
            "## Metadata",
            f"- **Plan ID**: {self.plan_id}",
            f"- **Session ID**: {self.session_id}",
            f"- **Status**: {self.status.value}",
            f"- **Created**: {self.created_at.isoformat()}",
            f"- **Updated**: {self.updated_at.isoformat()}",
            "",
            "## Intent",
            f"**Type**: {self.work_type}",
            f"**Goal**: {self.goal}",
            f"**Scope**: {self.scope}",
            "",
            "## File Impact Matrix",
            "",
            "| Path | Action | Description |",
            "|------|--------|-------------|",
        ]
        for entry in self.file_impact_matrix:
            lines.append(f"| {entry.get('path', '')} | {entry.get('action', '')} | {entry.get('description', '')} |")
        
        lines.extend([
            "",
            "## Tasks",
            "",
        ])
        
        for task in self.tasks:
            lines.extend([
                f"### Task {task.task_id}: {task.title}",
                f"**Depends on**: {', '.join(task.depends_on) or 'None'}",
                f"**Files**: {', '.join(task.files) or 'N/A'}",
                f"**Action**: {task.action}",
                f"**Agent**: {task.agent}",
                f"**Priority**: {task.priority}",
                f"**Description**: {task.description}",
                f"**Verification**: {task.verification}",
                "",
            ])
        
        if self.test_plan:
            lines.extend([
                "## Test Plan",
                "",
                self.test_plan,
                "",
            ])
        
        if self.risks or self.open_questions:
            lines.extend([
                "## Risks & Open Questions",
                "",
            ])
            for risk in self.risks:
                lines.append(f"- **Risk**: {risk}")
            for question in self.open_questions:
                lines.append(f"- **Question**: {question}")
        
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str, plan_id: str, session_id: str) -> "PlanDocument":
        """Parse a markdown plan document. Basic parsing for recovery."""
        import re
        
        def extract_section(pattern: str, text: str) -> str:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            return match.group(1).strip() if match else ""
        
        goal = extract_section(r"# Plan:\s*(.+?)(?:\n|$)", content)
        work_type = extract_section(r"\*\*Type\*\*:\s*(.+?)(?:\n|$)", content)
        scope = extract_section(r"\*\*Scope\*\*:\s*(.+?)(?:\n|$)", content)
        
        # Parse tasks
        tasks = []
        task_pattern = r"### Task\s+([^:]+):\s*(.+?)(?=\n###|\n##|$)"
        for match in re.finditer(task_pattern, content, re.DOTALL):
            task_id = match.group(1).strip()
            task_content = match.group(2)
            title = task_content.split("\n")[0].strip()
            
            def get_field(name: str) -> str:
                m = re.search(rf"\*\*{name}\*\*:\s*(.+?)(?:\n|$)", task_content)
                return m.group(1).strip() if m else ""
            
            tasks.append(PlanTask(
                task_id=task_id,
                title=title,
                description=get_field("Description"),
                depends_on=[d.strip() for d in get_field("Depends on").split(",") if d.strip() and d.strip() != "None"],
                files=[f.strip() for f in get_field("Files").split(",") if f.strip() and f.strip() != "N/A"],
                action=get_field("Action") or "EDIT",
                agent=get_field("Agent") or "analyst",
                priority=get_field("Priority") or "medium",
                verification=get_field("Verification"),
            ))
        
        return cls(
            plan_id=plan_id,
            session_id=session_id,
            goal=goal,
            work_type=work_type or "new_feature",
            scope=scope,
            tasks=tasks,
            status=PlanStatus.DRAFT,
        )


class PlanningRequest(BaseModel):
    """Request to create a plan."""
    session_id: str
    message: str
    folder_path: str | None = None
    context: str = ""  # Gathered context before planning
    complexity_score: float = 0.5


class PlanningResponse(BaseModel):
    """Response from the planning agent."""
    plan: PlanDocument
    needs_confirmation: bool = True
    summary: str = ""


class PlanConfirmationRequest(BaseModel):
    """Request to confirm/reject a plan."""
    session_id: str
    plan_id: str
    action: str  # confirm, reject, modify
    modifications: dict[str, Any] = Field(default_factory=dict)


class PlanConfirmationResponse(BaseModel):
    """Response from plan confirmation."""
    plan: PlanDocument
    todo_list_id: str | None = None
    message: str = ""
