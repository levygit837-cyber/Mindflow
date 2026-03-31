"""Planning Service for managing plan documents in temporary session storage.

This service manages the lifecycle of plan documents:
- Create plans from PlannerAgent output
- Store plans as .md files in session temp directory
- Confirm/reject plans
- Convert confirmed plans to todo lists
"""

from __future__ import annotations

import asyncio
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.orchestration.planning import (
    PlanConfirmationRequest,
    PlanConfirmationResponse,
    PlanDocument,
    PlanningRequest,
    PlanningResponse,
    PlanStatus,
    PlanTask,
)
from mindflow_backend.schemas.tools.planning import TodoItemContract, TodoItemStatus
from mindflow_backend.services import get_todo_planning_service

_logger = get_logger(__name__)


class PlanningService:
    """Manage planning documents for orchestrator sessions.
    
    Plans are stored as .md files in a session-scoped temporary directory.
    The service tracks plan status and converts confirmed plans to todo lists.
    """

    def __init__(self) -> None:
        self._plans: dict[str, dict[str, PlanDocument]] = defaultdict(dict)
        self._plan_files: dict[str, Path] = {}
        self._lock = asyncio.Lock()
        self._plans_dir: Path | None = None

    def _get_plans_dir(self) -> Path:
        """Get or create the plans directory for the current session."""
        if self._plans_dir is None:
            settings = get_settings()
            base_dir = getattr(settings, "working_path", None) or tempfile.gettempdir()
            self._plans_dir = Path(base_dir) / ".plans"
            self._plans_dir.mkdir(parents=True, exist_ok=True)
        return self._plans_dir

    def _get_session_dir(self, session_id: str) -> Path:
        """Get or create a session-specific directory."""
        plans_dir = self._get_plans_dir()
        session_dir = plans_dir / f"session_{session_id[:8]}"
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    async def create_plan(
        self,
        request: PlanningRequest,
        plan_content: dict[str, Any],
    ) -> PlanningResponse:
        """Create a new plan document from PlannerAgent output."""
        plan_id = f"plan-{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        
        # Parse tasks from plan content
        tasks = []
        for i, raw_task in enumerate(plan_content.get("tasks", [])):
            tasks.append(PlanTask(
                task_id=str(raw_task.get("task_id") or raw_task.get("item_id") or f"task-{i+1}"),
                title=str(raw_task.get("title") or raw_task.get("task") or f"Task {i+1}"),
                description=str(raw_task.get("description") or raw_task.get("scope") or ""),
                depends_on=[str(d) for d in raw_task.get("depends_on", []) if d],
                files=[str(f) for f in raw_task.get("files", []) if f],
                action=str(raw_task.get("action", "EDIT")),
                agent=str(raw_task.get("agent", "analyst")),
                priority=str(raw_task.get("priority", "medium")),
                verification=str(raw_task.get("verification", "")),
            ))
        
        # Parse file impact matrix
        file_impact = plan_content.get("file_impact_matrix", [])
        if not file_impact and plan_content.get("files"):
            # Convert simple files list to matrix
            for f in plan_content.get("files", []):
                file_impact.append({"path": str(f), "action": "EDIT", "description": ""})
        
        plan = PlanDocument(
            plan_id=plan_id,
            session_id=request.session_id,
            goal=plan_content.get("goal") or request.message,
            intent=plan_content.get("intent", ""),
            work_type=plan_content.get("work_type", "new_feature"),
            scope=plan_content.get("scope", ""),
            file_impact_matrix=file_impact,
            tasks=tasks,
            test_plan=plan_content.get("test_plan", ""),
            risks=plan_content.get("risks", []),
            open_questions=plan_content.get("open_questions", []),
            status=PlanStatus.PENDING_CONFIRMATION,
            created_at=now,
            updated_at=now,
            folder_path=request.folder_path,
            source_context=request.context,
        )
        
        # Store in memory
        async with self._lock:
            self._plans[request.session_id][plan_id] = plan
        
        # Write to .md file
        await self._write_plan_file(plan)
        
        _logger.info(
            "plan_created",
            plan_id=plan_id,
            session_id=request.session_id,
            tasks=len(tasks),
            status=plan.status.value,
        )
        
        summary = self._build_plan_summary(plan)
        
        return PlanningResponse(
            plan=plan,
            needs_confirmation=True,
            summary=summary,
        )

    async def get_plan(self, session_id: str, plan_id: str) -> PlanDocument | None:
        """Get a plan by ID."""
        async with self._lock:
            return self._plans.get(session_id, {}).get(plan_id)

    async def get_session_plans(self, session_id: str) -> list[PlanDocument]:
        """Get all plans for a session."""
        async with self._lock:
            return list(self._plans.get(session_id, {}).values())

    async def confirm_plan(
        self,
        request: PlanConfirmationRequest,
    ) -> PlanConfirmationResponse:
        """Confirm, reject, or modify a plan."""
        from mindflow_backend.orchestrator.planning.metrics import get_metrics_collector
        
        async with self._lock:
            plan = self._plans.get(request.session_id, {}).get(request.plan_id)
            if plan is None:
                raise ValueError(f"Plan not found: {request.plan_id}")
            
            now = datetime.now(UTC)
            metrics = get_metrics_collector()
            
            if request.action == "confirm":
                plan.status = PlanStatus.CONFIRMED
                plan.confirmed_at = now
                plan.updated_at = now
                
                # Track confirmation
                metrics.track_user_confirmation(
                    session_id=request.session_id,
                    plan_id=request.plan_id,
                    confirmed=True,
                )
                
                # Convert to todo list
                todo_list_id = await self._convert_plan_to_todo(plan)
                
                # Update the .md file
                await self._write_plan_file(plan)
                
                _logger.info(
                    "plan_confirmed",
                    plan_id=plan.plan_id,
                    session_id=request.session_id,
                    todo_list_id=todo_list_id,
                )
                
                return PlanConfirmationResponse(
                    plan=plan,
                    todo_list_id=todo_list_id,
                    message=f"Plano confirmado. {len(plan.tasks)} tarefas adicionadas à lista de execução.",
                )
            
            elif request.action == "reject":
                plan.status = PlanStatus.REJECTED
                plan.updated_at = now
                
                # Track rejection
                metrics.track_user_confirmation(
                    session_id=request.session_id,
                    plan_id=request.plan_id,
                    confirmed=False,
                )
                
                await self._write_plan_file(plan)
                
                _logger.info(
                    "plan_rejected",
                    plan_id=plan.plan_id,
                    session_id=request.session_id,
                )
                
                return PlanConfirmationResponse(
                    plan=plan,
                    message="Plano rejeitado. Você pode solicitar um novo planejamento.",
                )
            
            elif request.action == "modify":
                # Apply modifications
                if "tasks" in request.modifications:
                    plan.tasks = [PlanTask(**t) for t in request.modifications["tasks"]]
                if "goal" in request.modifications:
                    plan.goal = request.modifications["goal"]
                if "scope" in request.modifications:
                    plan.scope = request.modifications["scope"]
                if "file_impact_matrix" in request.modifications:
                    plan.file_impact_matrix = request.modifications["file_impact_matrix"]
                
                plan.updated_at = now
                await self._write_plan_file(plan)
                
                _logger.info(
                    "plan_modified",
                    plan_id=plan.plan_id,
                    session_id=request.session_id,
                )
                
                return PlanConfirmationResponse(
                    plan=plan,
                    message="Plano modificado. Confirme quando estiver satisfeito.",
                )
            
            else:
                raise ValueError(f"Unknown action: {request.action}")

    async def update_plan_status(
        self,
        session_id: str,
        plan_id: str,
        status: PlanStatus,
    ) -> PlanDocument:
        """Update plan status during execution."""
        async with self._lock:
            plan = self._plans.get(session_id, {}).get(plan_id)
            if plan is None:
                raise ValueError(f"Plan not found: {plan_id}")
            
            plan.status = status
            plan.updated_at = datetime.now(UTC)
            await self._write_plan_file(plan)
            
            return plan

    async def _write_plan_file(self, plan: PlanDocument) -> None:
        """Write plan to .md file."""
        session_dir = self._get_session_dir(plan.session_id)
        plan_file = session_dir / f"{plan.plan_id}.md"
        
        plan_file.write_text(plan.to_markdown(), encoding="utf-8")
        self._plan_files[plan.plan_id] = plan_file
        
        _logger.debug("plan_file_written", path=str(plan_file))

    async def _convert_plan_to_todo(self, plan: PlanDocument) -> str:
        """Convert confirmed plan to todo list."""
        todo_service = get_todo_planning_service()
        
        todo_items = []
        for task in plan.tasks:
            todo_items.append(TodoItemContract(
                item_id=task.task_id,
                title=task.title,
                description=task.description,
                owner_agent=task.agent,
                priority=task.priority,
                dependencies=task.depends_on,
                status=TodoItemStatus.PENDING,
            ))
        
        result = await todo_service.replace_list(
            session_id=plan.session_id,
            task_id=plan.plan_id,
            goal=plan.goal,
            items=todo_items,
            source="planning_service",
        )
        
        return plan.plan_id

    def _build_plan_summary(self, plan: PlanDocument) -> str:
        """Build a human-readable summary of the plan."""
        lines = [
            f"**Objetivo**: {plan.goal}",
            f"**Tipo**: {plan.work_type}",
            f"**Escopo**: {plan.scope or 'Não especificado'}",
            f"**Tarefas**: {len(plan.tasks)}",
        ]
        
        if plan.tasks:
            lines.append("")
            lines.append("**Tarefas**:")
            for task in plan.tasks[:5]:
                deps = f" (deps: {', '.join(task.depends_on)})" if task.depends_on else ""
                lines.append(f"  - [{task.priority}] {task.title}{deps}")
            if len(plan.tasks) > 5:
                lines.append(f"  - ... e mais {len(plan.tasks) - 5} tarefas")
        
        if plan.risks:
            lines.append("")
            lines.append(f"**Riscos**: {len(plan.risks)} identificados")
        
        return "\n".join(lines)

    async def load_plan_from_file(self, session_id: str, plan_id: str) -> PlanDocument | None:
        """Load a plan from its .md file (for recovery)."""
        session_dir = self._get_session_dir(session_id)
        plan_file = session_dir / f"{plan_id}.md"
        
        if not plan_file.exists():
            return None
        
        content = plan_file.read_text(encoding="utf-8")
        plan = PlanDocument.from_markdown(content, plan_id, session_id)
        
        async with self._lock:
            self._plans[session_id][plan_id] = plan
            self._plan_files[plan_id] = plan_file
        
        return plan


# Global service instance
_planning_service: PlanningService | None = None


def get_planning_service() -> PlanningService:
    """Get the global planning service instance."""
    global _planning_service
    if _planning_service is None:
        _planning_service = PlanningService()
    return _planning_service
