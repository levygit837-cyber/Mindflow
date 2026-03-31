"""Hook Handlers — Event-specific hook handlers.

Handlers são wrappers de conveniência que encapsulam a lógica de
construção de HookContext para cada tipo de evento.

Uso direto pelo runtime em vez de chamar HookManager.execute() diretamente.
"""

from __future__ import annotations

from mindflow_backend.hooks.handlers.pre_tool_use import PreToolUseHandler
from mindflow_backend.hooks.handlers.post_tool_use import PostToolUseHandler
from mindflow_backend.hooks.handlers.post_tool_failure import PostToolFailureHandler
from mindflow_backend.hooks.handlers.stop import StopHandler
from mindflow_backend.hooks.handlers.session_start import SessionStartHandler
from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler
from mindflow_backend.hooks.handlers.permission_hook import (
    PermissionRequestHandler,
    PermissionDeniedHandler,
)

__all__ = [
    "PreToolUseHandler",
    "PostToolUseHandler",
    "PostToolFailureHandler",
    "StopHandler",
    "SessionStartHandler",
    "UserPromptSubmitHandler",
    "PermissionRequestHandler",
    "PermissionDeniedHandler",
]