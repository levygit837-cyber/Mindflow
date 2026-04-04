"""Security shell executor v2 compatibility adapter.

This legacy security-facing surface now delegates execution to the canonical
unsuffixed system shell executor while preserving the legacy constructor and
security-oriented entrypoint.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.agents.tools.system.shell_executor import ShellExecutorTool
from mindflow_backend.schemas.tools.system_schemas import SHELL_EXECUTOR_SCHEMA
from mindflow_backend.security.audit.security_logger import get_security_logger
from mindflow_backend.security.policies.network_policy import NetworkPolicy


class ShellExecutorToolV2(AsyncToolInterface):
    """Legacy security shell executor backed by the canonical shell tool."""

    def __init__(
        self,
        root_dir: str | None = None,
        use_docker: bool = True,
        network_policy: NetworkPolicy | None = None,
        security_logger: Any | None = None,
    ):
        super().__init__()
        self.root_dir = root_dir
        self.use_docker = use_docker
        self.name = "shell_execute"
        self.description = "Execute shell commands with Docker-oriented security controls"
        self.network_policy = network_policy or NetworkPolicy()
        self.security_logger = security_logger or get_security_logger()
        self._schema = SHELL_EXECUTOR_SCHEMA
        self._canonical_tool = ShellExecutorTool(
            network_policy=self.network_policy,
            security_logger=self.security_logger,
            use_docker=use_docker,
        )

    async def execute(self, **kwargs) -> dict[str, Any]:
        """Delegate execution to the canonical shell tool."""
        payload = dict(kwargs)
        if "working_dir" not in payload and self.root_dir:
            payload["working_dir"] = self.root_dir
        payload.setdefault("use_docker", self.use_docker)
        return await self._canonical_tool.execute(**payload)

    def get_schema(self) -> dict[str, Any]:
        """Return the legacy schema for compatibility."""
        return self._schema.dict()
