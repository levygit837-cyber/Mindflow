"""EnterPlanModeTool — Tool para entrar em Plan Mode.

Baseado no EnterPlanModeTool do Claude Code.
Quando ativado, o sistema:
1. Muda o modo de permissão para PLAN
2. Restringe execução de tools destrutivas
3. Foca em exploração e planejamento
4. Gera um plano estruturado antes de implementação
"""

from __future__ import annotations

from typing import Any, ClassVar
from loguru import logger

from mindflow_backend.agents.tools.base.tool_interface import BaseTool
from mindflow_backend.permissions.types import PermissionMode

_logger = logger.bind(__name__)


class EnterPlanModeTool(BaseTool):
    """Tool para entrar em Plan Mode.
    
    Quando invocada:
    1. Salva snapshot do modo atual (pre_plan_mode)
    2. Muda permission_mode para PLAN
    3. Ativa prompts de planejamento
    4. Restringe tools destrutivas
    
    Para sair do Plan Mode:
    - Use confirm_plan com action="confirm" para executar
    - Ou action="reject" para cancelar e voltar ao modo anterior
    """
    
    name: ClassVar[str] = "enter_plan_mode"
    description: ClassVar[str] = (
        "Enter Plan Mode for structured planning before implementation. "
        "In Plan Mode: (1) destructive tools are restricted, "
        "(2) focus on exploration and design, "
        "(3) generate a plan before executing. "
        "Use confirm_plan to exit Plan Mode and proceed with execution."
    )
    
    session_id: str = ""
    folder_path: str | None = None
    
    def _run(self, message: str = "") -> str:
        """Synchronous wrapper."""
        raise RuntimeError("enter_plan_mode requires async execution")
    
    async def _arun(self, message: str = "") -> str:
        """Execute plan mode entry."""
        from mindflow_backend.hooks.event_broadcaster import dispatch_custom_event
        from mindflow_backend.services.core.session_service import get_session_service
        
        _logger.info(
            "enter_plan_mode_invoked",
            session_id=self.session_id,
            message_preview=message[:100] if message else "",
        )
        
        try:
            # 1. Get session service
            session_service = get_session_service()
            
            # 2. Get current permission mode
            current_mode = await session_service.get_permission_mode(self.session_id)
            
            # 3. Save pre-plan mode snapshot and switch to PLAN mode
            await session_service.set_permission_mode(
                session_id=self.session_id,
                mode=PermissionMode.PLAN,
                pre_plan_mode=current_mode,
            )
            
            # 4. Dispatch mode change event
            await dispatch_custom_event("mode_changed", {
                "old_mode": current_mode.value if hasattr(current_mode, "value") else str(current_mode),
                "new_mode": PermissionMode.PLAN.value,
                "session_id": self.session_id,
            })
            
            _logger.info(
                "plan_mode_activated",
                session_id=self.session_id,
                old_mode=current_mode.value if hasattr(current_mode, "value") else str(current_mode),
            )
            
            # 5. Return response with planning instructions
            response_parts = [
                "**🔒 Plan Mode Ativado**",
                "",
                "Neste modo:",
                "- Ferramentas destrutivas estão restritas",
                "- Foco em exploração e planejamento",
                "- Um plano será gerado antes da execução",
                "",
                "**Próximos passos:**",
                "1. Explore o codebase para entender o contexto",
                "2. Use `create_plan` para gerar um plano estruturado",
                "3. Use `confirm_plan` para executar ou cancelar",
            ]
            
            if message:
                response_parts.extend(["", f"**Contexto:** {message}"])
            
            return "\n".join(response_parts)
            
        except Exception as e:
            _logger.error(
                "enter_plan_mode_failed",
                session_id=self.session_id,
                error=str(e),
            )
            return f"**Erro ao entrar em Plan Mode:** {str(e)}"