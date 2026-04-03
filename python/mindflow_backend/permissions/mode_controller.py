"""Mode Cycle Controller.

Manages the permission mode cycle:
  default → accept_edits → plan → auto → bypass → dont_ask → default

Based on Claude Code's Shift+Tab behavior.

Adapted for MindFlow:
  default → accept_edits → plan → auto → bypass → dont_ask → default
"""

from __future__ import annotations

from typing import Any
import logging

from mindflow_backend.permissions.types import PermissionMode

_logger = logging.getLogger(__name__)


# Mode cycle order (adaptação do Claude Code para MindFlow)
MODE_CYCLE = [
    PermissionMode.DEFAULT,
    PermissionMode.ACCEPT_EDITS,
    PermissionMode.PLAN,
    PermissionMode.AUTO,
    PermissionMode.BYPASS,
    PermissionMode.DONT_ASK,
]


class ModeController:
    """Controls permission mode cycling and transitions.
    
    Mode cycle:
      default → accept_edits → plan → auto → bypass → dont_ask → default
    
    Transitions:
    - Forward (Shift+Tab equivalent): Next mode in cycle
    - Backward: Previous mode in cycle
    - Direct: Jump to specific mode
    """
    
    def __init__(self) -> None:
        self._current_index = 0
    
    def get_next_mode(self, current_mode: PermissionMode) -> PermissionMode:
        """Get next mode in cycle."""
        try:
            current_index = MODE_CYCLE.index(current_mode)
            next_index = (current_index + 1) % len(MODE_CYCLE)
            return MODE_CYCLE[next_index]
        except ValueError:
            _logger.warning(f"Unknown mode {current_mode}, returning DEFAULT")
            return PermissionMode.DEFAULT
    
    def get_previous_mode(self, current_mode: PermissionMode) -> PermissionMode:
        """Get previous mode in cycle."""
        try:
            current_index = MODE_CYCLE.index(current_mode)
            prev_index = (current_index - 1) % len(MODE_CYCLE)
            return MODE_CYCLE[prev_index]
        except ValueError:
            _logger.warning(f"Unknown mode {current_mode}, returning DEFAULT")
            return PermissionMode.DEFAULT
    
    def get_mode_info(self, mode: PermissionMode) -> dict[str, Any]:
        """Get display information for a mode."""
        MODE_INFO: dict[PermissionMode, dict[str, str]] = {
            PermissionMode.DEFAULT: {
                "name": "Default",
                "description": "User approval required per tool",
                "icon": "🔒",
                "color": "yellow",
            },
            PermissionMode.ACCEPT_EDITS: {
                "name": "Accept Edits",
                "description": "Allow edits in working directory",
                "icon": "✏️",
                "color": "blue",
            },
            PermissionMode.PLAN: {
                "name": "Plan Mode",
                "description": "Read-only planning, no execution",
                "icon": "📋",
                "color": "purple",
            },
            PermissionMode.AUTO: {
                "name": "Auto Mode",
                "description": "Classifier decides, no user prompt",
                "icon": "🤖",
                "color": "green",
            },
            PermissionMode.BYPASS: {
                "name": "Bypass",
                "description": "All tools allowed (sandbox only)",
                "icon": "⚡",
                "color": "orange",
            },
            PermissionMode.DONT_ASK: {
                "name": "Don't Ask",
                "description": "Deny tools that would prompt",
                "icon": "🚫",
                "color": "red",
            },
        }
        return MODE_INFO.get(mode, {
            "name": mode.value if hasattr(mode, "value") else str(mode),
            "description": "Unknown mode",
            "icon": "❓",
            "color": "gray",
        })
    
    def validate_transition(
        self,
        from_mode: PermissionMode,
        to_mode: PermissionMode,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, str]:
        """Validate if a mode transition is allowed.
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Plan Mode can only be exited via confirm_plan
        if from_mode == PermissionMode.PLAN:
            if to_mode != PermissionMode.DEFAULT:
                return False, (
                    "Plan Mode can only be exited via confirm_plan. "
                    "Use confirm_plan to execute or reject to cancel."
                )
        
        # Auto Mode requires gate check
        if to_mode == PermissionMode.AUTO:
            if not context or not context.get("auto_mode_available"):
                return False, "Auto Mode not available (gate check failed)"
        
        # BYPASS requires sandbox
        if to_mode == PermissionMode.BYPASS:
            if not context or not context.get("is_sandbox"):
                return False, "Bypass mode only available in sandbox"
        
        return True, "Transition allowed"
    
    def get_cycle_order(self) -> list[PermissionMode]:
        """Get the full mode cycle order."""
        return MODE_CYCLE.copy()
    
    def get_mode_index(self, mode: PermissionMode) -> int:
        """Get the index of a mode in the cycle."""
        try:
            return MODE_CYCLE.index(mode)
        except ValueError:
            return -1