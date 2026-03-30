"""Execution memory helpers for delegation engine.

Provides helper methods for managing child executions,
events, and message persistence during task delegation.
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class ExecutionMemoryMixin:
    """Mixin providing execution memory helper methods."""

    _execution_memory: Any | None = None

    async def _start_child_execution(
        self,
        *,
        task: Any,
        session_id: str | None,
        root_execution_id: str | None,
        parent_execution_id: str | None,
    ) -> Any | None:
        """Start a child execution record for the delegated task."""
        if self._execution_memory is None or not session_id or not root_execution_id:
            return None
        try:
            return await self._execution_memory.start_execution(
                session_id=session_id,
                agent_id=task.agent_id or task.agent.value,
                goal=task.objective,
                root_execution_id=root_execution_id,
                parent_execution_id=parent_execution_id or root_execution_id,
                execution_role="delegated_agent",
                owner_execution_id=root_execution_id,
                status="running",
                stage="booting",
                metadata={
                    "task_id": str(task.task_id),
                    "objective": task.objective,
                    "scope": list(task.scope or []),
                    "expected_output": task.expected_output,
                    "context_from_session": task.context_from_session,
                },
            )
        except Exception as exc:
            _logger.warning("delegation_child_execution_start_failed", error=str(exc))
            return None

    async def _append_execution_event(
        self,
        execution_id: str | None,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        stage: str | None = None,
        message: str | None = None,
    ) -> None:
        """Append an event to the execution timeline."""
        if self._execution_memory is None or not execution_id:
            return
        try:
            await self._execution_memory.append_event(
                execution_id,
                event_type,
                payload or {},
                stage=stage,
                message=message,
            )
        except Exception as exc:
            _logger.warning(
                "delegation_event_persist_failed",
                execution_id=execution_id,
                error=str(exc),
            )

    async def _mark_execution_status(
        self,
        execution_id: str | None,
        status: str,
        **updates: Any,
    ) -> None:
        """Update the execution status."""
        if self._execution_memory is None or not execution_id:
            return
        try:
            await self._execution_memory.mark_status(execution_id, status, **updates)
        except Exception as exc:
            _logger.warning(
                "delegation_status_persist_failed",
                execution_id=execution_id,
                error=str(exc),
            )

    async def _record_result_message(
        self,
        *,
        child_execution_id: str,
        recipient_execution_id: str | None,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Record a result message from child to parent execution."""
        if self._execution_memory is None:
            return
        try:
            await self._execution_memory.record_message(
                execution_id=child_execution_id,
                message_type=message_type,
                sender_execution_id=child_execution_id,
                recipient_execution_id=recipient_execution_id,
                content=content,
                visibility="internal",
                payload=payload,
                status="pending",
            )
        except Exception as exc:
            _logger.warning(
                "delegation_message_persist_failed",
                execution_id=child_execution_id,
                error=str(exc),
            )

    def _make_event_dispatcher(self, execution_id: str | None):
        """Create an event dispatcher function for tool invocations."""

        async def _dispatch(event_name: str, payload: dict[str, Any]) -> None:
            if execution_id:
                await self._append_execution_event(
                    execution_id,
                    event_name,
                    payload,
                    stage="working",
                )
            try:
                from langchain_core.callbacks.manager import adispatch_custom_event

                await adispatch_custom_event(event_name, payload)
            except Exception:
                pass

        return _dispatch

    def _make_before_iteration(self, execution_id: str | None):
        """Create a before-iteration hook for consuming pending messages."""

        async def _before_iteration(messages: list[Any], _iteration: int) -> None:
            if self._execution_memory is None or not execution_id:
                return

            try:
                pending = await self._execution_memory.consume_pending_messages(
                    execution_id=execution_id
                )
            except Exception as exc:
                _logger.warning(
                    "delegation_pending_message_load_failed",
                    execution_id=execution_id,
                    error=str(exc),
                )
                return

            for message in pending:
                content = getattr(message, "content", "")
                if not content:
                    continue
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Additional context update received while you were working.\n"
                            f"{content}"
                        ),
                    }
                )
                await self._append_execution_event(
                    execution_id,
                    "message_consumed",
                    {
                        "message_id": getattr(message, "id", None),
                        "message_type": getattr(message, "message_type", None),
                    },
                    stage="applying_context",
                )

            if pending:
                await self._mark_execution_status(
                    execution_id, "running", stage="working"
                )

        return _before_iteration