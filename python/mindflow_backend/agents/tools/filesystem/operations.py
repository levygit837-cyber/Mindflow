"""Legacy filesystem tools (compatibility layer).

The unified filesystem tools live in `file_operations.py` and `search_tools.py`.
Some modules still import basic tools from `operations.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.base.tool_schemas import create_tool_schema
from mindflow_backend.agents.tools.security import (
    WorkspaceSecurityError,
    is_read_only_mode,
    resolve_workspace_path,
)


def _resolve_tool_path(tool: AsyncToolInterface, raw_path: str) -> Path:
    if tool.root_dir or tool.secure_mode:
        return resolve_workspace_path(raw_path, tool.root_dir)
    path = Path(raw_path)
    if tool.root_dir and not path.is_absolute():
        path = Path(tool.root_dir) / path
    return path.resolve()


class DirectoryListTool(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self.name = "list_dir"
        self.description = "List directory contents"
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {"name": "path", "type": "string", "description": "Directory path", "required": True},
            ],
            returns={"type": "object", "description": "Directory listing"},
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        raw_path = kwargs["path"]
        try:
            path = _resolve_tool_path(self, raw_path)
        except WorkspaceSecurityError as e:
            return {"success": False, "error": f"Workspace security error: {str(e)}"}
        if not path.exists() or not path.is_dir():
            return {"success": False, "error": f"Not a directory: {path}"}
        return {"success": True, "entries": [p.name for p in path.iterdir()]}

    def get_schema(self) -> Dict[str, Any]:
        return self._schema.dict()


class FileDeleteTool(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self.name = "delete_file"
        self.description = "Delete a file"
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {"name": "path", "type": "string", "description": "File path", "required": True},
            ],
            returns={"type": "object", "description": "Deletion result"},
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            if is_read_only_mode(self.sandbox_mode):
                return {"success": False, "error": "Delete operation blocked in read-only sandbox mode"}
            path = _resolve_tool_path(self, kwargs["path"])
        except WorkspaceSecurityError as e:
            return {"success": False, "error": f"Workspace security error: {str(e)}"}
        if not path.exists() or not path.is_file():
            return {"success": False, "error": f"Not a file: {path}"}
        path.unlink()
        return {"success": True}

    def get_schema(self) -> Dict[str, Any]:
        return self._schema.dict()


class DirectoryCreateTool(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self.name = "mkdir"
        self.description = "Create a directory"
        self._schema = create_tool_schema(
            name=self.name,
            description=self.description,
            category="filesystem",
            parameters=[
                {"name": "path", "type": "string", "description": "Directory path", "required": True},
                {"name": "parents", "type": "boolean", "description": "Create parents", "required": False, "default": True},
                {"name": "exist_ok", "type": "boolean", "description": "Ignore if exists", "required": False, "default": True},
            ],
            returns={"type": "object", "description": "Create directory result"},
        )

    async def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            if is_read_only_mode(self.sandbox_mode):
                return {"success": False, "error": "Create directory blocked in read-only sandbox mode"}
            path = _resolve_tool_path(self, kwargs["path"])
        except WorkspaceSecurityError as e:
            return {"success": False, "error": f"Workspace security error: {str(e)}"}
        parents = bool(kwargs.get("parents", True))
        exist_ok = bool(kwargs.get("exist_ok", True))
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return {"success": True}

    def get_schema(self) -> Dict[str, Any]:
        return self._schema.dict()
