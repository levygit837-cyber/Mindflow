"""Permission system for MindFlow — mirrors Claude Code's permission architecture.

Provides:
- PermissionMode: auto, plan, default, bypass
- PermissionRule: pattern-based allow/deny/ask rules
- PermissionManager: centralized permission checking with circuit breaker
- Tool permission handlers for different tool categories

Design principles:
- All permission checks return a PermissionResult
- Rules evaluated in order: deny → ask → mode → tool check → hooks → user
- Pattern matching supports wildcards: "Bash(git *)", "FileRead(/tmp/*)"
- Audit-friendly: all decisions logged with reason
"""

from mindflow_backend.permissions.types import (
    PermissionBehavior,
    PermissionMode,
    PermissionResult,
    PermissionRule,
    PermissionRuleSource,
    PermissionRuleValue,
    PermissionContext,
    RuleSource,
)
from mindflow_backend.permissions.manager import PermissionManager

__all__ = [
    "PermissionBehavior",
    "PermissionMode",
    "PermissionResult",
    "PermissionRule",
    "PermissionRuleSource",
    "PermissionRuleValue",
    "PermissionContext",
    "RuleSource",
    "PermissionManager",
]