"""Tool for the Orchestrator to create a structured implementation plan.

This tool is called by the Orchestrator when:
1. Context has been gathered
2. The task is complex enough to warrant explicit planning
3. The user has requested planning

The tool invokes the PlannerAgent and returns a plan for confirmation.
"""

from __future__ import annotations

from typing import Any, ClassVar

from langchain_core.tools import BaseTool

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class CreatePlanTool(BaseTool):
    """Tool to create a structured implementation plan.
    
    When invoked, this tool:
    1. Calls the PlannerAgent with gathered context
    2. Creates a plan document (.md)
    3. Returns the plan for user confirmation
    """

    name: ClassVar[str] = "create_plan"
    description: ClassVar[str] = (
        "Create a structured implementation plan for a complex task. "
        "Use this when: (1) the task is complex and requires multiple steps, "
        "(2) you have gathered sufficient context about the codebase, "
        "(3) planning would help organize the implementation. "
        "Returns a plan document for user confirmation."
    )
    
    session_id: str = ""
    folder_path: str | None = None
    context: str = ""
    complexity_score: float = 0.5

    def _run(self, message: str) -> str:
        """Synchronous wrapper (not used, raises error)."""
        raise RuntimeError("create_plan tool requires async execution")

    async def _arun(self, message: str) -> str:
        """Execute the planning tool asynchronously."""
        from mindflow_backend.agents.planner_agent import get_planner_agent
        from mindflow_backend.schemas.orchestration.planning import PlanningRequest
        
        _logger.info(
            "create_plan_tool_invoked",
            session_id=self.session_id,
            message_preview=message[:100],
            has_context=bool(self.context),
        )
        
        planner = get_planner_agent()
        request = PlanningRequest(
            session_id=self.session_id,
            message=message,
            folder_path=self.folder_path,
            context=self.context,
            complexity_score=self.complexity_score,
        )
        
        try:
            result = await planner.create_plan(request)
            
            # Build response for orchestrator
            response_parts = [
                f"**Plano criado: {result.plan.plan_id}**",
                "",
                result.summary,
                "",
                "---",
                "",
                "**Status**: Aguardando confirmação",
                "",
                "Use `confirm_plan` para confirmar ou rejeitar o plano.",
                f"- Para confirmar: `confirm_plan(plan_id=\"{result.plan.plan_id}\", action=\"confirm\")`",
                f"- Para rejeitar: `confirm_plan(plan_id=\"{result.plan.plan_id}\", action=\"reject\")`",
            ]
            
            return "\n".join(response_parts)
            
        except Exception as exc:
            _logger.error("create_plan_tool_failed", error=str(exc))
            return f"Erro ao criar plano: {exc}"


class ConfirmPlanTool(BaseTool):
    """Tool to confirm, reject, or modify a plan.
    
    This tool is called by the Orchestrator after the user has reviewed
    the plan and decided to proceed, reject, or request modifications.
    """

    name: ClassVar[str] = "confirm_plan"
    description: ClassVar[str] = (
        "Confirm, reject, or modify a plan. "
        "Use after `create_plan` has been called and the user has reviewed the plan. "
        "Actions: 'confirm' to proceed with execution, 'reject' to discard, "
        "'modify' to request changes."
    )
    
    session_id: str = ""

    def _run(self, plan_id: str, action: str, modifications: dict[str, Any] | None = None) -> str:
        """Synchronous wrapper (not used, raises error)."""
        raise RuntimeError("confirm_plan tool requires async execution")

    async def _arun(
        self,
        plan_id: str,
        action: str,
        modifications: dict[str, Any] | None = None,
    ) -> str:
        """Execute the confirmation tool asynchronously."""
        from mindflow_backend.schemas.orchestration.planning import PlanConfirmationRequest
        from mindflow_backend.services.orchestration.planning_service import get_planning_service
        
        _logger.info(
            "confirm_plan_tool_invoked",
            session_id=self.session_id,
            plan_id=plan_id,
            action=action,
        )
        
        planning_service = get_planning_service()
        request = PlanConfirmationRequest(
            session_id=self.session_id,
            plan_id=plan_id,
            action=action,
            modifications=modifications or {},
        )
        
        try:
            result = await planning_service.confirm_plan(request)
            
            if action == "confirm":
                return (
                    f"**Plano confirmado!**\n\n"
                    f"{result.message}\n\n"
                    f"Todo-list criada com {len(result.plan.tasks)} tarefas. "
                    f"O sistema iniciará a execução sequencial."
                )
            elif action == "reject":
                return f"**Plano rejeitado.**\n\n{result.message}"
            else:
                return f"**Plano modificado.**\n\n{result.message}"
                
        except Exception as exc:
            _logger.error("confirm_plan_tool_failed", error=str(exc))
            return f"Erro ao processar confirmação: {exc}"


class GetPlanStatusTool(BaseTool):
    """Tool to check the status of a plan or list all plans in a session."""

    name: ClassVar[str] = "get_plan_status"
    description: ClassVar[str] = (
        "Get the status of a specific plan or list all plans in the current session. "
        "Use to check if a plan exists, its status, and progress."
    )
    
    session_id: str = ""

    def _run(self, plan_id: str | None = None) -> str:
        """Synchronous wrapper (not used, raises error)."""
        raise RuntimeError("get_plan_status tool requires async execution")

    async def _arun(self, plan_id: str | None = None) -> str:
        """Execute the status check tool asynchronously."""
        from mindflow_backend.services.orchestration.planning_service import get_planning_service
        
        planning_service = get_planning_service()
        
        try:
            if plan_id:
                plan = await planning_service.get_plan(self.session_id, plan_id)
                if plan is None:
                    return f"Plano não encontrado: {plan_id}"
                
                return (
                    f"**Plano: {plan.plan_id}**\n"
                    f"- Status: {plan.status.value}\n"
                    f"- Objetivo: {plan.goal}\n"
                    f"- Tarefas: {len(plan.tasks)}\n"
                    f"- Criado: {plan.created_at.isoformat()}\n"
                )
            else:
                plans = await planning_service.get_session_plans(self.session_id)
                if not plans:
                    return "Nenhum plano encontrado nesta sessão."
                
                lines = ["**Planos na sessão:**", ""]
                for plan in plans:
                    lines.append(
                        f"- `{plan.plan_id}`: {plan.status.value} - {plan.goal[:50]}..."
                    )
                return "\n".join(lines)
                
        except Exception as exc:
            _logger.error("get_plan_status_tool_failed", error=str(exc))
            return f"Erro ao verificar plano: {exc}"
