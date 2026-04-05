"""Timeout configuration constants.

Defines timeout values for different operations based on Claude Code's implementation.
"""

from __future__ import annotations

import os
from typing import Final


def _get_env_int(name: str, default: int) -> int:
    """Get integer from environment variable.

    Args:
        name: Environment variable name
        default: Default value if not set or invalid

    Returns:
        Integer value
    """
    value = os.getenv(name)
    if value:
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return default


# Bash command timeouts
DEFAULT_BASH_TIMEOUT_MS: Final[int] = _get_env_int("BASH_DEFAULT_TIMEOUT_MS", 120_000)  # 2 minutes
MAX_BASH_TIMEOUT_MS: Final[int] = _get_env_int("BASH_MAX_TIMEOUT_MS", 600_000)  # 10 minutes

# HTTP hook timeouts
DEFAULT_HTTP_HOOK_TIMEOUT_MS: Final[int] = _get_env_int("HTTP_HOOK_TIMEOUT_MS", 600_000)  # 10 minutes

# Tool hook timeouts
TOOL_HOOK_EXECUTION_TIMEOUT_MS: Final[int] = _get_env_int("TOOL_HOOK_TIMEOUT_MS", 600_000)  # 10 minutes
SESSION_END_HOOK_TIMEOUT_MS: Final[int] = _get_env_int("SESSION_END_HOOK_TIMEOUT_MS", 1_500)  # 1.5 seconds

# LSP server timeouts
DEFAULT_LSP_TIMEOUT_MS: Final[int] = _get_env_int("LSP_TIMEOUT_MS", 30_000)  # 30 seconds
LSP_INIT_TIMEOUT_MS: Final[int] = _get_env_int("LSP_INIT_TIMEOUT_MS", 60_000)  # 1 minute
LSP_SHUTDOWN_TIMEOUT_MS: Final[int] = _get_env_int("LSP_SHUTDOWN_TIMEOUT_MS", 10_000)  # 10 seconds

# Output limits
BASH_MAX_OUTPUT_DEFAULT: Final[int] = _get_env_int("BASH_MAX_OUTPUT_LENGTH", 30_000)  # 30KB
BASH_MAX_OUTPUT_UPPER_LIMIT: Final[int] = 150_000  # 150KB


def get_bash_timeout_ms() -> int:
    """Get the current bash timeout in milliseconds.

    Returns:
        Timeout in milliseconds
    """
    return DEFAULT_BASH_TIMEOUT_MS


def get_max_bash_timeout_ms() -> int:
    """Get the maximum bash timeout in milliseconds.

    Returns:
        Maximum timeout in milliseconds
    """
    # Ensure max is at least as large as default
    return max(MAX_BASH_TIMEOUT_MS, DEFAULT_BASH_TIMEOUT_MS)


def get_http_hook_timeout_ms() -> int:
    """Get the HTTP hook timeout in milliseconds.

    Returns:
        Timeout in milliseconds
    """
    return DEFAULT_HTTP_HOOK_TIMEOUT_MS


def get_tool_hook_timeout_ms() -> int:
    """Get the tool hook timeout in milliseconds.

    Returns:
        Timeout in milliseconds
    """
    return TOOL_HOOK_EXECUTION_TIMEOUT_MS
