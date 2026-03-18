"""Session-scoped shell tab tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.schemas.tools.shell_tabs import (
    SHELL_TAB_CLOSE_SCHEMA,
    SHELL_TAB_EXEC_SCHEMA,
    SHELL_TAB_LIST_SCHEMA,
    SHELL_TAB_OPEN_SCHEMA,
    SHELL_TAB_READ_SCHEMA,
    SHELL_TAB_STATUS_SCHEMA,
)
from mindflow_backend.schemas.orchestration.orchestrator import SandboxMode
from mindflow_backend.services import get_shell_tab_service


class _ShellTabToolBase(AsyncToolInterface):
    def __init__(self) -> None:
        super().__init__()
        self._service = get_shell_tab_service()

    def _resolve_session_id(self, kwargs: dict[str, Any]) -> str:
        session_id = kwargs.get("session_id") or self.session_id
        if not session_id:
            raise ValueError("session_id is required for shell tab operations")
        return str(session_id)


class ShellTabOpenTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_open"
        self.description = "Create a session-scoped shell tab for stateful shell inspection"
        self._schema = SHELL_TAB_OPEN_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        cwd = kwargs.get("cwd") or self.root_dir or str(Path.cwd())
        title = kwargs.get("title")
        created = await self._service.create_tab(
            session_id=session_id,
            cwd=cwd,
            title=title,
            workspace_root=self.root_dir,
            read_only=self.sandbox_mode == SandboxMode.READ_ONLY,
            secure_mode=self.secure_mode,
        )
        return self._format_result(success=True, result=created.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ShellTabListTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_list"
        self.description = "List shell tabs for the current session"
        self._schema = SHELL_TAB_LIST_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        tabs = await self._service.list_tabs(session_id=session_id)
        return self._format_result(
            success=True,
            result=[tab.model_dump(mode="json") for tab in tabs],
        )

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ShellTabStatusTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_status"
        self.description = "Inspect the latest state of a shell tab"
        self._schema = SHELL_TAB_STATUS_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        tab_id = kwargs["tab_id"]
        status = await self._service.get_tab_status(session_id=session_id, tab_id=tab_id)
        return self._format_result(success=True, result=status.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ShellTabExecTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_exec"
        self.description = "Execute a command within an existing shell tab"
        self._schema = SHELL_TAB_EXEC_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        tab_id = kwargs["tab_id"]
        command = kwargs["command"]
        updated = await self._service.exec_in_tab(session_id=session_id, tab_id=tab_id, command=command)
        return self._format_result(success=True, result=updated.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ShellTabReadTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_read"
        self.description = "Read the stdout/stderr buffers accumulated inside a shell tab"
        self._schema = SHELL_TAB_READ_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        tab_id = kwargs["tab_id"]
        snapshot = await self._service.read_tab_buffer(session_id=session_id, tab_id=tab_id)
        return self._format_result(success=True, result=snapshot.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()


class ShellTabCloseTool(_ShellTabToolBase):
    def __init__(self) -> None:
        super().__init__()
        self.name = "shell_tab_close"
        self.description = "Terminate a shell tab and any active process attached to it"
        self._schema = SHELL_TAB_CLOSE_SCHEMA

    async def execute(self, **kwargs) -> dict[str, Any]:
        session_id = self._resolve_session_id(kwargs)
        tab_id = kwargs["tab_id"]
        closed = await self._service.close_tab(session_id=session_id, tab_id=tab_id)
        return self._format_result(success=True, result=closed.model_dump(mode="json"))

    def get_schema(self) -> dict[str, Any]:
        return self._schema.model_dump()
