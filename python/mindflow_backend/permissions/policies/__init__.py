"""Default permission policies for MindFlow.

Mirrors Claude Code's built-in deny/allow lists and safety checks.
These policies are applied automatically unless overridden by user settings.
"""

from mindflow_backend.permissions.policies.default import (
    DEFAULT_DENY_TOOLS,
    DANGEROUS_FILES,
    DANGEROUS_DIRECTORIES,
    SAFE_TOOLS,
    get_default_deny_rules,
    get_default_allow_rules,
    is_dangerous_path,
)

__all__ = [
    "DEFAULT_DENY_TOOLS",
    "DANGEROUS_FILES",
    "DANGEROUS_DIRECTORIES",
    "SAFE_TOOLS",
    "get_default_deny_rules",
    "get_default_allow_rules",
    "is_dangerous_path",
]