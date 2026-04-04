"""Planning tools for orchestrator todo-list workflows."""

from __future__ import annotations

import warnings
from importlib import import_module

from .scratchpad import ScratchpadReadTool, ScratchpadWriteTool
from .todo_list import FocusTodosTool, ReadTodosTool, WriteTodosTool

_COMPAT_EXPORTS = {
    "TodoListWriteToolV3": (".todo_list_write_v3", "TodoListWriteToolV3"),
    "TodoListReadToolV3": (".todo_list_read_v3", "TodoListReadToolV3"),
    "TodoListFocusToolV3": (".todo_list_focus_v3", "TodoListFocusToolV3"),
}

__all__ = [
    "ScratchpadReadTool",
    "ScratchpadWriteTool",
    "WriteTodosTool",
    "ReadTodosTool",
    "FocusTodosTool",
]


def __getattr__(name: str):
    if name not in _COMPAT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _COMPAT_EXPORTS[name]
    warnings.warn(
        (
            f"{__name__}.{name} is a deprecated compatibility export. "
            f"Import {attr_name} from {__name__}{module_name} instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
