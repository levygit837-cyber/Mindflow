"""Docker-backed container orchestration for PinchTab runtimes."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


def _slugify(value: str) -> str:
    """Create a docker-safe container name fragment."""
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-").lower()


class PinchTabContainerService:
    """Provision and control one PinchTab runtime container per browser."""

    runtime_port = 9867

    def __init__(self, docker_client: Any | None = None) -> None:
        self.settings = get_settings()
        self._docker = docker_client

    async def create_container(
        self,
        browser_id: str,
        session_id: str,
        agent_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a browser runtime container and return runtime metadata."""
        payload = payload or {}
        container_name = f"mindflow-pinchtab-{_slugify(browser_id)}"
        labels = {
            "mindflow.managed": "true",
            "mindflow.agent_id": agent_id,
            "mindflow.session_id": session_id,
            "mindflow.browser_id": browser_id,
        }
        environment = {
            "BROWSER_ID": browser_id,
            "SESSION_ID": session_id,
            "AGENT_ID": agent_id,
        }
        ports = {f"{self.runtime_port}/tcp": None}

        def _run_container() -> Any:
            docker_client = self._get_client()
            return docker_client.containers.run(
                self.settings.pinchtab_browser_image,
                detach=True,
                name=container_name,
                labels=labels,
                environment=environment,
                network=self.settings.pinchtab_docker_network,
                ports=ports,
            )

        container = await asyncio.to_thread(_run_container)
        await asyncio.to_thread(container.reload)
        runtime_endpoint = self._resolve_runtime_endpoint(container)
        return {
            "container_id": container.id,
            "container_name": container.name,
            "runtime_endpoint": runtime_endpoint,
            "runtime_state": container.attrs.get("State", {}).get("Status", "created"),
            "tab_id": str(self._resolve_runtime_port(container)),
        }

    async def inspect_container(self, container_id: str) -> dict[str, Any] | None:
        """Inspect a managed runtime container."""
        try:
            container = await asyncio.to_thread(self._get_client().containers.get, container_id)
            await asyncio.to_thread(container.reload)
        except Exception:
            return None

        attrs = container.attrs or {}
        state = attrs.get("State", {})
        return {
            "container_id": container.id,
            "container_name": container.name,
            "runtime_endpoint": self._resolve_runtime_endpoint(container),
            "runtime_state": state.get("Status", "unknown"),
            "paused": bool(state.get("Paused")),
            "running": bool(state.get("Running")),
            "tab_id": str(self._resolve_runtime_port(container)),
        }

    async def pause_container(self, container_id: str) -> None:
        """Pause a managed runtime container."""
        container = await asyncio.to_thread(self._get_client().containers.get, container_id)
        await asyncio.to_thread(container.pause)

    async def resume_container(self, container_id: str) -> None:
        """Resume a paused runtime container."""
        container = await asyncio.to_thread(self._get_client().containers.get, container_id)
        await asyncio.to_thread(container.unpause)

    async def stop_container(self, container_id: str) -> None:
        """Stop and remove a managed runtime container."""
        container = await asyncio.to_thread(self._get_client().containers.get, container_id)

        def _stop_and_remove() -> None:
            container.stop(timeout=10)
            container.remove(v=True, force=True)

        await asyncio.to_thread(_stop_and_remove)

    def _resolve_runtime_port(self, container: Any) -> int:
        """Resolve the published host port for the runtime."""
        ports = (container.attrs or {}).get("NetworkSettings", {}).get("Ports", {})
        bindings = ports.get(f"{self.runtime_port}/tcp") or []
        if not bindings:
            return self.runtime_port
        return int(bindings[0]["HostPort"])

    def _resolve_runtime_endpoint(self, container: Any) -> str:
        """Build the runtime endpoint URL from docker port bindings."""
        return f"http://127.0.0.1:{self._resolve_runtime_port(container)}"

    def _get_client(self) -> Any:
        """Create the Docker SDK client only when it is first needed."""
        if self._docker is None:
            import docker

            self._docker = docker.from_env()
        return self._docker


__all__ = ["PinchTabContainerService"]
