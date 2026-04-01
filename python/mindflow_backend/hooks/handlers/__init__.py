"""Hook Handlers — Event-specific hook handlers.

Handlers são wrappers de conveniência que encapsulam a lógica de
construção de HookContext para cada tipo de evento.

Uso direto pelo runtime em vez de chamar HookManager.execute() diretamente.
"""

from __future__ import annotations

from mindflow_backend.hooks.handlers.instructions_loaded import InstructionsLoadedHandler
from mindflow_backend.hooks.handlers.permission_hook import (
    PermissionDeniedHandler,
    PermissionRequestHandler,
)
from mindflow_backend.hooks.handlers.post_tool_failure import PostToolFailureHandler
from mindflow_backend.hooks.handlers.post_tool_use import PostToolUseHandler
from mindflow_backend.hooks.handlers.pre_tool_use import PreToolUseHandler
from mindflow_backend.hooks.handlers.session_start import SessionStartHandler
from mindflow_backend.hooks.handlers.session_end import SessionEndHandler
from mindflow_backend.hooks.handlers.stop import StopHandler
from mindflow_backend.hooks.handlers.stop_failure import StopFailureHandler
from mindflow_backend.hooks.handlers.pre_compact import PreCompactHandler
from mindflow_backend.hooks.handlers.post_compact import PostCompactHandler
from mindflow_backend.hooks.handlers.notification import NotificationHandler
from mindflow_backend.hooks.handlers.task_lifecycle import TaskCreatedHandler, TaskCompletedHandler
from mindflow_backend.hooks.handlers.config_change import ConfigChangeHandler
from mindflow_backend.hooks.handlers.setup import SetupHandler
from mindflow_backend.hooks.handlers.file_watcher import FileChangedHandler, CwdChangedHandler
from mindflow_backend.hooks.handlers.user_prompt_submit import UserPromptSubmitHandler

__all__ = [
    "InstructionsLoadedHandler",
    "PermissionDeniedHandler",
    "PermissionRequestHandler",
    "PostToolFailureHandler",
    "PostToolUseHandler",
    "PreToolUseHandler",
    "SessionStartHandler",
    "SessionEndHandler",
    "StopHandler",
    "StopFailureHandler",
    "PreCompactHandler",
    "PostCompactHandler",
    "NotificationHandler",
    "TaskCreatedHandler",
    "TaskCompletedHandler",
    "ConfigChangeHandler",
    "SetupHandler",
    "FileChangedHandler",
    "CwdChangedHandler",
    "UserPromptSubmitHandler",
]
