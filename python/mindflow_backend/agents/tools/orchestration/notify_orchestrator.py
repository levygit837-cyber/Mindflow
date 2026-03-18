"""Tool for delegated agents to send direct updates back to the orchestrator."""

from __future__ import annotations

from typing import Any

from mindflow_backend.agents.tools.base.tool_interface import AsyncToolInterface
from mindflow_backend.execution_memory import get_execution_memory_service


class NotifyOrchestratorTool(AsyncToolInterface):
    def __init__(self, *, execution_memory: Any | None = None) -> None:
        super().__init__()
        self.name = "notify_orchestrator"
        self.description = (
            "Send a direct progress update or clarification request to the orchestrator "
            "without ending your current work."
        )
        self.parent_execution_id: str | None = None
        self._execution_memory = execution_memory or get_execution_memory_service()

    def get_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Progress update, clarification request, or blocker for the orchestrator.",
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Either direct_message or system_notice.",
                        "default": "direct_message",
                    },
                },
                "required": ["message"],
            },
        }

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        execution_id = self.execution_id
        if not execution_id or not self.parent_execution_id:
            return self._format_result(
                success=False,
                error="Delegated execution context is missing.",
            )

        message = str(kwargs.get("message", "")).strip()
        if not message:
            return self._format_result(success=False, error="message is required")

        message_type = str(kwargs.get("message_type", "direct_message") or "direct_message").strip().lower()
        if message_type not in {"direct_message", "system_notice"}:
            message_type = "direct_message"

        recorded = await self._execution_memory.record_message(
            execution_id=execution_id,
            message_type=message_type,
            sender_execution_id=execution_id,
            recipient_execution_id=self.parent_execution_id,
            content=message,
            visibility="internal",
            payload={},
            status="pending",
        )
        await self._execution_memory.append_event(
            execution_id,
            "direct_message_sent",
            {
                "message_type": message_type,
                "recipient_execution_id": self.parent_execution_id,
            },
            stage="working",
        )
        return self._format_result(
            success=True,
            result={
                "message_id": getattr(recorded, "id", None),
                "message_type": message_type,
                "recipient_execution_id": self.parent_execution_id,
            },
        )
