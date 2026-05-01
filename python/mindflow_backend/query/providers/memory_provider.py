"""Session memory context provider for QueryEngine."""

from __future__ import annotations

from typing import Any

from mindflow_backend.query.providers.base import BaseContextProvider


class MemoryProvider(BaseContextProvider):
    """Fetch a concise session-memory summary when a session id is available."""

    priority = 70

    def __init__(self, session_id: str | None = None, memory_service: Any | None = None) -> None:
        self.session_id = session_id
        self._memory_service = memory_service

    @property
    def name(self) -> str:
        return "memory"

    def _service(self) -> Any | None:
        if self._memory_service is not None:
            return self._memory_service
        try:
            from mindflow_backend.memory.session_memory.service import SessionMemoryService

            self._memory_service = SessionMemoryService()
        except Exception:
            self._memory_service = None
        return self._memory_service

    async def fetch(self, query: str, max_tokens: int = 0) -> str | None:
        del query, max_tokens

        if not self.session_id:
            return None

        service = self._service()
        if service is None or not hasattr(service, "get_session_memory_summary"):
            return None

        summary = await service.get_session_memory_summary(self.session_id)
        if not summary:
            return None
        return f"Session memory summary: {summary}"
