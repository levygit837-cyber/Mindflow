import asyncio
import httpx
from typing import Dict, Optional

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)

class WindsurfSessionManager:
    """Manages windsurf sessions mapped to workspace paths."""

    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url
        self._sessions: Dict[str, str] = {}  # workspace_path -> session_id
        self._lock = asyncio.Lock()

    async def get_or_create_session(self, workspace_path: str) -> str:
        """Get an existing session or start a new one for the workspace."""
        async with self._lock:
            if workspace_path in self._sessions:
                return self._sessions[workspace_path]

            session_id = await self._start_session(workspace_path)
            if session_id:
                self._sessions[workspace_path] = session_id
                
            return session_id

    async def _start_session(self, workspace_path: str) -> str:
        """Start a new session on the gateway."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gateway_url}/chat/session",
                    json={"workspacePath": workspace_path},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                session_id = data.get("sessionId")
                
                if not session_id:
                    raise ValueError("No sessionId returned from gateway")
                    
                _logger.info("windsurf_session_started", session_id=session_id, workspace_path=workspace_path)
                return session_id
                
        except Exception as e:
            _logger.error("windsurf_session_start_failed", error=str(e), workspace_path=workspace_path)
            raise

    async def close_session(self, workspace_path: str) -> None:
        """Remove a session from tracking."""
        async with self._lock:
            if workspace_path in self._sessions:
                session_id = self._sessions.pop(workspace_path)
                _logger.info("windsurf_session_closed", session_id=session_id)
