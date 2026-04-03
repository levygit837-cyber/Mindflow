"""Plan Mode Validation Hook.

Validates tool execution when in Plan Mode.
Blocks destructive tools and allows only read-only operations.
"""

from __future__ import annotations

from typing import Any
from loguru import logger

from mindflow_backend.hooks.types import HookEvent, HookResult
from mindflow_backend.hooks.context import HookContext

_logger = logger.bind(__name__)

# Tools allowed in Plan Mode (read-only + planning tools)
ALLOWED_IN_PLAN_MODE: frozenset[str] = frozenset({
    # Read-only tools
    "read_file",
    "search_files",
    "glob",
    "list_files",
    "codebase_search",
    "codebase_graph_query",
    "codebase_status",
    "codebase_context",
    "codebase_context_search",
    # Planning tools
    "create_plan",
    "confirm_plan",
    "enter_plan_mode",
})


class PlanModeValidationHook:
    """Hook to validate tool execution in Plan Mode.
    
    When in Plan Mode:
    - Block destructive tools (Edit, Write, Bash)
    - Allow read-only tools (Read, Search, Glob)
    - Allow planning tools (create_plan, confirm_plan)
    """
    
    @staticmethod
    async def validate(
        context: HookContext,
    ) -> HookResult:
        """Validate tool execution in Plan Mode.
        
        Args:
            context: Hook context with tool and session info
            
        Returns:
            HookResult indicating whether to continue or block
        """
        # Only validate if in Plan Mode
        if context.permission_mode != "plan":
            return HookResult.CONTINUE
        
        tool_name = context.tool_name
        if not tool_name:
            return HookResult.CONTINUE
        
        # Check if tool is allowed in Plan Mode
        if tool_name in ALLOWED_IN_PLAN_MODE:
            _logger.debug(
                "plan_mode_tool_allowed",
                tool_name=tool_name,
                session_id=context.session_id,
            )
            return HookResult.CONTINUE
        
        # Block tool execution
        _logger.info(
            "plan_mode_tool_blocked",
            tool_name=tool_name,
            session_id=context.session_id,
        )
        
        return HookResult(
            continue_execution=False,
            error=(
                f"**🔒 Plan Mode: Tool '{tool_name}' não permitida**\n\n"
                f"Em Plan Mode, apenas ferramentas de leitura e planejamento são permitidas.\n\n"
                f"**Ferramentas permitidas:**\n"
                f"- read_file, search_files, glob, list_files\n"
                f"- codebase_search, codebase_graph_query\n"
                f"- create_plan, confirm_plan\n\n"
                f"**Para sair do Plan Mode:**\n"
                f"- Use `confirm_plan` para executar o plano\n"
                f"- Ou `confirm_plan` com action='reject' para cancelar"
            ),
        )


def register_plan_mode_validation_hook() -> int:
    """Register Plan Mode validation hook with HookManager.
    
    Returns:
        Number of hooks registered (1)
    """
    from mindflow_backend.hooks.manager import HookManager
    from mindflow_backend.hooks.types import HookEvent
    import functools
    
    manager = HookManager.get_instance()
    
    # Register function hook for PreToolUse
    # The hook validates all tools when in Plan Mode
    manager.register_function(
        HookEvent.PRE_TOOL_USE,
        None,  # Match all tools
        functools.partial(_plan_mode_validation_wrapper),
    )
    
    _logger.info("Registered Plan Mode validation hook for PreToolUse")
    return 1


async def _plan_mode_validation_wrapper(context: HookContext) -> HookResult:
    """Wrapper for Plan Mode validation hook."""
    return await PlanModeValidationHook.validate(context)
