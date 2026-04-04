"""Legacy filesystem tools (compatibility layer).

`file_operations.py` and `search_tools.py` own the canonical filesystem
implementations. This module keeps import compatibility for older paths
that still expect the basic operations here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.base.tool_schemas import create_tool_schema
from mindflow_backend.agents.tools.filesystem.file_operations import (
    DirectoryListTool as CanonicalDirectoryListTool,
    FileDeleteTool as CanonicalFileDeleteTool,
)
from mindflow_backend.agents.tools.workspace_security import (
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

    async def execute(self, **kwargs) -> dict[str, Any]:
        tool = CanonicalDirectoryListTool()
        tool.root_dir = self.root_dir
        tool.sandbox_mode = self.sandbox_mode
        result = await tool.execute(
            directory_path=kwargs["path"],
            include_hidden=kwargs.get("include_hidden", False),
            include_size=kwargs.get("include_size", True),
            include_type=kwargs.get("include_type", True),
            max_items=kwargs.get("max_items", 10000),
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        payload = result.get("result") or {}
        return {"success": True, "entries": payload.get("entries", [])}

    def get_schema(self) -> dict[str, Any]:
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

    async def execute(self, **kwargs) -> dict[str, Any]:
        tool = CanonicalFileDeleteTool()
        tool.root_dir = self.root_dir
        tool.sandbox_mode = self.sandbox_mode
        result = await tool.execute(file_path=kwargs["path"])
        if not result.get("success"):
            return {"success": False, "error": result.get("error")}
        return {"success": True}

    def get_schema(self) -> dict[str, Any]:
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

    async def execute(self, **kwargs) -> dict[str, Any]:
        try:
            if is_read_only_mode(self.sandbox_mode):
                return {"success": False, "error": "Create directory blocked in read-only sandbox mode"}
            raw_path = kwargs.get("directory_path", kwargs.get("path"))
            if not raw_path:
                return {"success": False, "error": "Directory path is required"}
            path = _resolve_tool_path(self, raw_path)
        except WorkspaceSecurityError as e:
            return {"success": False, "error": f"Workspace security error: {str(e)}"}
        parents = bool(kwargs.get("parents", True))
        exist_ok = bool(kwargs.get("exist_ok", True))
        path.mkdir(parents=parents, exist_ok=exist_ok)
        return {"success": True}

    def get_schema(self) -> dict[str, Any]:
        return self._schema.dict()
